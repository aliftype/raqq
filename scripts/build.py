# Copyright (c) 2020-2023 Khaled Hosny
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import copy
import datetime
import os
import re

from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.transform import Identity, Transform
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib.tables._h_e_a_d import mac_epoch_diff
from fontTools.varLib import build as merge

from glyphsLib import GSFont, GSAnchor
from glyphsLib.glyphdata import get_glyph as getGlyphInfo, GlyphData


DEFAULT_TRANSFORM = [1, 0, 0, 1, 0, 0]

# https://www.microsoft.com/typography/otspec/os2.htm#cpr
CODEPAGE_RANGES = {
    1252: 0,
    1250: 1,
    1251: 2,
    1253: 3,
    1254: 4,
    1255: 5,
    1256: 6,
    1257: 7,
    1258: 8,
    # 9-15: Reserved for Alternate ANSI
    874: 16,
    932: 17,
    936: 18,
    949: 19,
    950: 20,
    1361: 21,
    # 22-28: Reserved for Alternate ANSI and OEM
    # 29: Macintosh Character Set (US Roman)
    # 30: OEM Character Set
    # 31: Symbol Character Set
    # 32-47: Reserved for OEM
    869: 48,
    866: 49,
    865: 50,
    864: 51,
    863: 52,
    862: 53,
    861: 54,
    860: 55,
    857: 56,
    855: 57,
    852: 58,
    775: 59,
    737: 60,
    708: 61,
    850: 62,
    437: 63,
}


def draw(layer, glyphSet, isTTF):
    xMin = None
    pen = RecordingPen()
    if layer.attributes.get("colorPalette") is not None:
        # If we are drawing a color layer, and it has components, we need to
        # remap the component to point to the new color glyphs we created. We
        # match Glyphs’s app by using the first layer in the component glyph
        # with the same color index.
        for component in layer.components:
            for componentLayer in component.component.layers:
                if layer.attributes.get(
                    "colorPalette"
                ) == componentLayer.attributes.get("colorPalette"):
                    component.componentName = componentLayer.name

    if layer.paths:
        from pathops import Path

        path = Path()
        layer.draw(path.getPen(glyphSet=glyphSet))
        path.simplify(fix_winding=True, keep_starting_points=True)
        path.draw(pen)
    else:
        layer.draw(pen)

    if isTTF:
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        from fontTools.pens.cu2quPen import Cu2QuPen

        ttpen = TTGlyphPen(glyphSet)
        pen.replay(Cu2QuPen(ttpen, 1.0, reverse_direction=True))
        glyph = ttpen.glyph()
    else:
        from fontTools.pens.t2CharStringPen import T2CharStringPen

        t2pen = T2CharStringPen(layer.width, glyphSet)
        pen.replay(t2pen)
        glyph = t2pen.getCharString()

    return glyph


def makeKern(font, master, instance):
    kerning = font.kerningRTL.get(master.id, [])
    pairs = ""
    classes = ""
    enums = ""
    for left in kerning:
        if left in font.glyphs and not font.glyphs[left].export:
            continue
        for right in kerning[left]:
            if right in font.glyphs and not font.glyphs[right].export:
                continue
            value = kerning[left][right]
            kern = f"<{value} 0 {value} 0>"
            if left.startswith("@") and right.startswith("@"):
                if value:
                    classes += f"pos {left} {right} {kern};\n"
            elif left.startswith("@") or right.startswith("@"):
                enums += f"enum pos {left} {right} {kern};\n"
            else:
                pairs += f"pos {left} {right} {kern};\n"

    return f"""
lookup kern_auto {{
lookupflag IgnoreMarks;
{pairs}
{enums}
{classes}
}} kern_auto;
"""


def getLayer(glyph, instance):
    for layer in glyph.layers:
        if layer.attributes.get("coordinates") == instance.axes:
            return layer
    return glyph.layers[0]


def makeMark(instance, glyphOrder):
    font = instance.parent

    classes = ""
    mark2base = ""
    mark2liga = ""

    ligatures = {}

    for gname in glyphOrder:
        glyph = font.glyphs[gname]
        if glyph is None:
            continue

        if (glyph.category, glyph.subCategory) == ("Letter", "Ligature"):
            ligatures[gname] = {i + 1: [] for i in range(gname.count("_") + 1)}

        layer = getLayer(glyph, instance)
        for anchor in layer.anchors:
            name, x, y = anchor.name, anchor.position.x, anchor.position.y
            if name.startswith("_"):
                classes += f"markClass {gname} <anchor {x} {y}> @mark_{name[1:]};\n"
            elif name.startswith("caret_") or name in ("exit", "entry"):
                pass
            elif "_" in name:
                name, index = name.split("_")
                ligatures[gname][int(index)].append((name, (x, y)))
            else:
                mark2base += f"pos base {gname} <anchor {x} {y}> mark @mark_{name};\n"

    for name, components in ligatures.items():
        mark2liga += f"pos ligature {name}"
        for component, anchors in components.items():
            if component != 1:
                mark2liga += " ligComponent"
            for anchor, (x, y) in anchors:
                mark2liga += f" <anchor {x} {y}> mark @mark_{anchor}"
        mark2liga += ";\n"

    return f"""
{classes}
lookup mark2base_auto {{
{mark2base}
}} mark2base_auto;
lookup mark2liga_auto {{
{mark2liga}
}} mark2liga_auto;
"""


def makeCurs(instance, glyphOrder):
    font = instance.parent

    fea = ""

    exit_ = {}
    entry_ = {}

    for gname in glyphOrder:
        glyph = font.glyphs[gname]
        if glyph is None:
            continue

        layer = getLayer(glyph, instance)
        for anchor in layer.anchors:
            name, x, y = anchor.name, anchor.position.x, anchor.position.y
            if name == "exit":
                exit_[gname] = (x, y)
            elif name == "entry":
                entry_[gname] = (x, y)

    for name in glyphOrder:
        if name in exit_ or name in entry_:
            pos1 = entry_.get(name)
            pos2 = exit_.get(name)
            anchor1 = pos1 and f"{pos1[0]} {pos1[1]}" or "NULL"
            anchor2 = pos2 and f"{pos2[0]} {pos2[1]}" or "NULL"
            fea += f"pos cursive {name} <anchor {anchor1}> <anchor {anchor2}>;\n"

    return f"""
lookup curs_auto {{
lookupflag IgnoreMarks RightToLeft;
{fea}
}} curs_auto;
"""


RE_DELIM = re.compile(r"(?:/(.*?.)/)")

LANG_IDS = {"ARA": "0x0C01", "ENG": "0x0409"}


def makeFeatures(instance, master, args, glyphOrder):
    font = instance.parent

    def repl(match):
        regex = re.compile(match.group(1))
        return " ".join(n for n in glyphOrder if regex.match(n))

    for x in list(font.featurePrefixes) + list(font.classes) + list(font.features):
        x.code = RE_DELIM.sub(repl, x.code)

    groups = {}
    for gclass in font.classes:
        if gclass.disabled:
            continue
        groups[gclass.name] = gclass.code

    for name in glyphOrder:
        glyph = font.glyphs[name]
        if glyph is None:
            continue
        if glyph.leftKerningGroup:
            group = f"MMK_R_{glyph.leftKerningGroup}"
            if group not in groups:
                groups[group] = []
            groups[group].append(name)
        if glyph.rightKerningGroup:
            group = f"MMK_L_{glyph.rightKerningGroup}"
            if group not in groups:
                groups[group] = []
            groups[group].append(name)

    fea = ""
    for name, code in groups.items():
        if not isinstance(code, str):
            code = " ".join(code)
        fea += f"@{name} = [{code}];\n"

    for prefix in font.featurePrefixes:
        if prefix.disabled:
            continue
        fea += prefix.code + "\n"

    for feature in font.features:
        if feature.disabled:
            continue
        code = feature.code
        names = ""
        for label in feature.labels:
            names += f'name 3 1 {LANG_IDS[label["language"]]} "{label["value"]}";\n'
        if names:
            code = "featureNames { " + names + " };\n" + code

        if "# Automatic Code\n" in code:
            before, after = code.split("# Automatic Code\n", 1)
            if feature.name == "mark":
                auto = makeMark(instance, glyphOrder)
            elif feature.name == "curs":
                auto = makeCurs(instance, glyphOrder)
            elif feature.name == "kern":
                auto = makeKern(font, master, instance)
            code = "\n".join([before, auto, after])
        fea += f"""
            feature {feature.name} {{
            {code}
            }} {feature.name};
        """

    marks = set()
    ligatures = set()
    carets = ""
    for name in glyphOrder:
        glyph = font.glyphs[name]
        if glyph is None:
            continue

        if (glyph.category, glyph.subCategory) == ("Mark", "Nonspacing"):
            marks.add(name)
        elif (glyph.category, glyph.subCategory) == ("Letter", "Ligature"):
            ligatures.add(name)
        else:
            layer = getLayer(glyph, instance)
            for anchor in layer.anchors:
                if anchor.name.startswith("_"):
                    marks.add(name)
                elif anchor.name.startswith("caret_"):
                    ligatures.add(name)

        layer = getLayer(glyph, instance)
        caret = ""
        for anchor in layer.anchors:
            if anchor.name.startswith("caret_"):
                _, index = anchor.name.split("_")
                if not caret:
                    caret = f"LigatureCaretByPos {name}"
                caret += f" {anchor.position.x}"
        if caret:
            carets += f"{caret};\n"

    fea += f"""
@MARK = [{" ".join(sorted(marks))}];
@LIGA = [{" ".join(sorted(ligatures))}];
table GDEF {{
 GlyphClassDef , @LIGA, @MARK, ;
{carets}
}} GDEF;
"""

    return fea


def calcFsSelection(instance):
    font = instance.parent
    fsSelection = 0
    if font.customParameters["Use Typo Metrics"]:
        fsSelection |= 1 << 7
    if instance.isItalic:
        fsSelection |= 1 << 1
    if instance.isBold:
        fsSelection |= 1 << 5
    if not (instance.isItalic or instance.isBold):
        fsSelection |= 1 << 6

    return fsSelection


def calcBits(bits, start, end):
    b = 0
    for i in reversed(range(start, end)):
        b = b << 1
        if i in bits:
            b = b | 0x1
    return b


def getProperty(font, name):
    for prop in font.properties:
        if prop.key == name:
            if prop.localized_values:
                return {k[:2].lower(): v for (k, v) in prop.localized_values.items()}
            return prop.value


def build(instance, isTTF, args):
    font = instance.parent
    master = font.masters[0]

    glyphOrder = list(font.glyphOrder)

    characterMap = {}
    colorLayers = {}

    glyphSet = {}
    for name in glyphOrder:
        glyph = font.glyphs[name]
        layer = getLayer(glyph, instance)
        glyphSet[name] = layer

        for layer in glyph.layers:
            if glyph.subCategory == "Nonspacing":
                layer.width = 0

            paletteIdx = layer.attributes.get("colorPalette", None)
            if paletteIdx is not None:
                colorLayers.setdefault(name, [])
                if layer.layerId != master.id:
                    layer.name = f"{name}.color{len(colorLayers[name])}"
                    glyphSet[layer.name] = layer
                    font.glyphOrder.append(layer.name)
                    colorLayers[name].append((layer.name, paletteIdx))
                else:
                    colorLayers[name].append((name, paletteIdx))

        for uni in glyph.unicodes:
            characterMap[int(uni, 16)] = name

    version = float(args.version)

    vendor = getProperty(font, "vendorID")
    names = {
        "copyright": getProperty(font, "copyrights"),
        "familyName": instance.familyName,
        "styleName": instance.name,
        "uniqueFontIdentifier": f"{version:.03f};{vendor};{instance.fontName}",
        "fullName": instance.fullName,
        "version": f"Version {version:.03f}",
        "psName": instance.fontName,
        "manufacturer": getProperty(font, "manufacturers"),
        "designer": getProperty(font, "designers"),
        "description": getProperty(font, "descriptions"),
        "vendorURL": font.manufacturerURL,
        "designerURL": font.designerURL,
        "licenseDescription": getProperty(font, "licenses"),
        "licenseInfoURL": getProperty(font, "licenseURL"),
        "sampleText": getProperty(font, "sampleTexts"),
    }

    fb = FontBuilder(font.upm, isTTF=isTTF)
    date = font.date.replace(tzinfo=datetime.timezone.utc)
    stat = args.input.stat()
    fb.updateHead(
        fontRevision=version,
        created=int(date.timestamp()) - mac_epoch_diff,
        modified=int(stat.st_mtime) - mac_epoch_diff,
    )
    fb.setupGlyphOrder(font.glyphOrder)
    fb.setupCharacterMap(characterMap)
    fb.setupNameTable(names, mac=False)
    fb.setupHorizontalHeader(
        ascent=master.customParameters["hheaAscender"],
        descent=master.customParameters["hheaDescender"],
        lineGap=master.customParameters["hheaLineGap"] or 0,
    )

    metrics = {}
    glyphs = {}
    for name, layer in glyphSet.items():
        glyphs[name] = draw(layer, glyphSet, isTTF)
        metrics[name] = [layer.width, 0]

    if isTTF:
        fb.setupGlyf(glyphs)
        glyf = fb.font["glyf"]
        for name, glyph in glyphs.items():
            glyph.recalcBounds(glyf)
            metrics[name][1] = glyph.xMin
    else:
        fb.setupCFF(names["psName"], {}, glyphs, {})
        for name, charString in glyphs.items():
            pen = ControlBoundsPen(glyphSet)
            charString.draw(pen)
            if pen.bounds:
                metrics[name][1] = pen.bounds[0]

    fb.setupHorizontalMetrics(metrics)

    fb.setupPost(
        underlinePosition=master.customParameters["underlinePosition"] or 0,
        underlineThickness=master.customParameters["underlineThickness"] or 0,
    )

    codePages = [CODEPAGE_RANGES[v] for v in font.customParameters["codePageRanges"]]
    fb.setupOS2(
        version=4,
        sTypoAscender=master.customParameters["typoAscender"],
        sTypoDescender=master.customParameters["typoDescender"],
        sTypoLineGap=master.customParameters["typoLineGap"] or 0,
        usWinAscent=master.customParameters["winAscent"],
        usWinDescent=master.customParameters["winDescent"],
        sxHeight=master.xHeight,
        sCapHeight=master.capHeight,
        achVendID=vendor,
        fsType=calcBits(font.customParameters["fsType"], 0, 16),
        fsSelection=calcFsSelection(instance),
        ulUnicodeRange1=calcBits(font.customParameters["unicodeRanges"], 0, 32),
        ulCodePageRange1=calcBits(codePages, 0, 32),
    )

    fb.font.cfg["fontTools.otlLib.builder:WRITE_GPOS7"] = True

    fea = makeFeatures(instance, master, args, glyphOrder)
    feapath = args.input
    if os.environ.get("FONTTOOLS_LOOKUP_DEBUGGING"):
        feapath = feapath.with_suffix(".fea")
        with open(feapath, "w") as f:
            f.write(fea)
    fb.addOpenTypeFeatures(fea, filename=feapath)

    palettes = font.customParameters["Color Palettes"]
    palettes = [[tuple(v / 255 for v in c) for c in p] for p in palettes]
    fb.setupCPAL(palettes)
    fb.setupCOLR(colorLayers)

    return fb.font


def propagateAnchors(glyph, layer):
    if glyph is not None and glyph.color == 0:
        return

    for component in layer.components:
        clayer = component.layer or component.component.layers[0]
        propagateAnchors(None, clayer)
        for anchor in clayer.anchors:
            names = [a.name for a in layer.anchors]
            name = anchor.name
            if name.startswith("_") or name in names:
                continue
            if name in ("entry", "exit"):
                continue
            x, y = anchor.position.x, anchor.position.y
            if component.transform != Identity:
                t = Transform(*component.transform.value)
                x, y = t.transformPoint((x, y))
            new = GSAnchor(name)
            new.position.x, new.position.y = (x, y)
            layer.anchors[name] = new


def prepare(args):
    font = GSFont(args.input)
    font.glyphOrder = [g.name for g in font.glyphs if g.export]

    for glyph in font.glyphs:
        info = getGlyphInfo(glyph.name, data=args.data)
        if glyph.category is None:
            glyph.category = info.category
        if glyph.subCategory is None:
            glyph.subCategory = info.subCategory
        for layer in glyph.layers:
            propagateAnchors(glyph, layer)

    return font


def data(path):
    with open(path) as f:
        return GlyphData.from_files(f)


def main():
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Build Raqq font.")
    parser.add_argument("input", help="input Glyphs source file", type=Path)
    parser.add_argument("version", help="font version", type=str)
    parser.add_argument("output", help="output OTF file", type=Path)
    parser.add_argument("--data", help="GlyphData.xml file", type=data)
    args = parser.parse_args()

    isTTF = False
    if args.output.suffix == ".ttf":
        isTTF = True

    font = prepare(args)
    instance = font.instances[0]  # XXX

    otf = build(instance, isTTF, args)
    otf.save(args.output)


main()
