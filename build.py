# Copyright (c) 2020 Khaled Hosny
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
import re
import datetime

from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.fontBuilder import FontBuilder
from fontTools.ttLib.tables._h_e_a_d import mac_epoch_diff
from fontTools.varLib import build as merge
from fontTools.misc.transform import Identity
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from glyphsLib import GSFont
from glyphsLib.glyphdata import get_glyph as getGlyphInfo
from glyphsLib.filters.eraseOpenCorners import EraseOpenCornersPen
from pathops import Path, PathPen


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


class DecomposePathPen(PathPen):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, path, layerSet):
        self._layerSet = layerSet

    def addComponent(self, name, transform):

        pen = self
        if transform != Identity:
            pen = TransformPen(pen, transform)
            xx, xy, yx, yy = transform[:4]
            if xx * yy - xy * yx < 0:
                pen = ReverseContourPen(pen)
        self._layerSet[name].draw(pen)


def draw(layer, layerSet):
    # Draw glyph and remove overlaps.
    path = Path()
    layer.draw(DecomposePathPen(path, layerSet))

    path2 = Path()
    erasepen = EraseOpenCornersPen(path2.getPen())
    path.draw(erasepen)
    path2.simplify(fix_winding=True, keep_starting_points=True)

    # Build CharString.
    t2pen = T2CharStringPen(layer.width, None)
    path2.draw(t2pen)

    return t2pen.getCharString()


def makeKerning(font, master, glyphOrder):
    fea = ""

    groups = {}
    for name in glyphOrder:
        glyph = font.glyphs[name]
        if glyph is None or not glyph.export:
            continue
        if glyph.leftKerningGroup:
            group = f"@MMK_R_{glyph.leftKerningGroup}"
            if group not in groups:
                groups[group] = []
            groups[group].append(name)
        if glyph.rightKerningGroup:
            group = f"@MMK_L_{glyph.rightKerningGroup}"
            if group not in groups:
                groups[group] = []
            groups[group].append(name)
    for group, glyphs in groups.items():
        fea += f"{group} = [{' '.join(glyphs)}];\n"

    kerning = font.kerningRTL[master.id]
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

    fea += f"""
feature kern {{
lookupflag IgnoreMarks;
{pairs}
{enums}
{classes}
}} kern;
"""

    return fea


def getLayer(glyph, instance):
    key = "{" + ", ".join(str(a) for a in instance.axes) + "}"
    for layer in glyph.layers:
        if layer.name == key:
            return layer
    return glyph.layers[0]


def makeMark(instance, glyphOrder):
    font = instance.parent

    fea = ""
    mark = ""
    curs = ""
    liga = ""

    exit = {}
    entry = {}
    lig = {}

    for gname in glyphOrder:
        glyph = font.glyphs[gname]
        if glyph is None or not glyph.export:
            continue

        if "_" in gname:
            lig[gname] = {i + 1: [] for i in range(gname.count("_") + 1)}

        layer = getLayer(glyph, instance)
        for anchor in layer.anchors:
            name, x, y = anchor.name, anchor.position.x, anchor.position.y
            if name.startswith("_"):
                fea += f"markClass {gname} <anchor {x} {y}> @mark_{name[1:]};\n"
            elif name.startswith("caret_"):
                pass
            elif "_" in name:
                name, index = name.split("_")
                lig[gname][int(index)].append((name, (x, y)))
            elif name == "exit":
                exit[gname] = (x, y)
            elif name == "entry":
                entry[gname] = (x, y)
            else:
                mark += f"pos base {gname} <anchor {x} {y}> mark @mark_{name};\n"

    for name, components in lig.items():
        mark += f"pos ligature {name}"
        for component, anchors in components.items():
            if component != 1:
                mark += " ligComponent"
            for anchor, (x, y) in anchors:
                mark += f" <anchor {x} {y}> mark @mark_{anchor}"
        mark += ";\n"

    for name in glyphOrder:
        if name in exit or name in entry:
            pos1 = entry.get(name)
            pos2 = exit.get(name)
            anchor1 = pos1 and f"{pos1[0]} {pos1[1]}" or "NULL"
            anchor2 = pos2 and f"{pos2[0]} {pos2[1]}" or "NULL"
            curs += f"pos cursive {name} <anchor {anchor1}> <anchor {anchor2}>;\n"

    fea += f"""
feature curs {{
lookupflag IgnoreMarks RightToLeft;
{curs}
}} curs;
feature mark {{
{mark}
}} mark;
"""

    return fea


RE_DELIM = re.compile(r"(?:/(.*?.)/)")

LANG_IDS = {"ARA": "0x0C01", "ENG": "0x0409"}


def makeFeatures(instance, master, opts, glyphOrder):
    font = instance.parent

    def repl(match):
        regex = re.compile(match.group(1))
        return " ".join(n for n in glyphOrder if regex.match(n))

    for x in list(font.featurePrefixes) + list(font.classes) + list(font.features):
        x.code = RE_DELIM.sub(repl, x.code)

    fea = ""
    for gclass in font.classes:
        if gclass.disabled:
            continue
        fea += f"@{gclass.name} = [{gclass.code}];\n"

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
            elif feature.name == "kern":
                auto = makeKerning(font, master, glyphOrder)
            if before:
                fea += f"""
                    feature {feature.name} {{
                    {before}
                    }} {feature.name};
                """
            fea += auto
            if after:
                fea += f"""
                    feature {feature.name} {{
                    {after}
                    }} {feature.name};
                """
        else:
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
        if glyph is None or not glyph.export:
            continue

        if getCategory(glyph) == ("Mark", "Nonspacing"):
            marks.add(name)
        elif getCategory(glyph) == ("Letter", "Ligature"):
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

    if opts.debug:
        with open(f"{instance.fontName}.fea", "w") as f:
            f.write(fea)
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


def getCategory(glyph):
    category, subCategory = glyph.category, glyph.subCategory
    if not category or not subCategory:
        info = getGlyphInfo(glyph.name)
        category = category or info.category
        subCategory = subCategory or info.subCategory

    return category, subCategory


def build(instance, opts, glyphOrder):
    font = instance.parent
    master = font.masters[0]
    glyphOrder = list(glyphOrder)

    advanceWidths = {}
    characterMap = {}
    charStrings = {}
    colorLayers = {}

    layerSet = {g.name: g.layers[master.id] for g in font.glyphs}

    for name in list(glyphOrder):
        glyph = font.glyphs[name]
        if not glyph.export:
            continue

        layer = getLayer(glyph, instance)
        if getCategory(glyph) == ("Mark", "Nonspacing"):
            layer.width = 0
        charStrings[name] = draw(layer, layerSet)
        advanceWidths[name] = layer.width

        for layer in glyph.layers:
            paletteIdx = layer.attr.get("colorPalette", None)
            if paletteIdx is not None:
                colorLayers.setdefault(name, [])

                new = name
                # XXX disable this optimization for Cairo/FreeType
                if True or layer.layerId != master.id:
                    new += f".layer{len(colorLayers[name])}"
                    charStrings[new] = draw(layer, layerSet)
                    advanceWidths[new] = advanceWidths[name]

                    glyphOrder.append(new)
                colorLayers[name].append((new, paletteIdx))

        for uni in glyph.unicodes:
            characterMap[int(uni, 16)] = name

    # XXX
    glyphOrder.pop(glyphOrder.index(".notdef"))
    glyphOrder.pop(glyphOrder.index("space"))
    glyphOrder.insert(0, ".notdef")
    glyphOrder.insert(1, "space")

    version = float(opts.version)

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

    fb = FontBuilder(font.upm, isTTF=False)
    date = font.date.replace(tzinfo=datetime.timezone.utc)
    stat = opts.glyphs.stat()
    fb.updateHead(
        fontRevision=version,
        created=int(date.timestamp()) - mac_epoch_diff,
        modified=int(stat.st_mtime) - mac_epoch_diff,
    )
    fb.setupGlyphOrder(glyphOrder)
    fb.setupCharacterMap(characterMap)
    fb.setupNameTable(names, mac=False)
    fb.setupHorizontalHeader(
        ascent=master.customParameters["hheaAscender"],
        descent=master.customParameters["hheaDescender"],
        lineGap=master.customParameters["hheaLineGap"] or 0,
    )

    if opts.debug:
        fb.setupCFF(names["psName"], {}, charStrings, {})
        fb.font["CFF "].compile(fb.font)
    else:
        fb.setupCFF2(charStrings)

    metrics = {}
    for name, width in advanceWidths.items():
        bounds = charStrings[name].calcBounds(None) or [0]
        metrics[name] = (width, bounds[0])
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
        usWinAscent=master.ascender,
        usWinDescent=-master.descender,
        sxHeight=master.xHeight,
        sCapHeight=master.capHeight,
        achVendID=vendor,
        fsType=calcBits(font.customParameters["fsType"], 0, 16),
        fsSelection=calcFsSelection(instance),
        ulUnicodeRange1=calcBits(font.customParameters["unicodeRanges"], 0, 32),
        ulCodePageRange1=calcBits(codePages, 0, 32),
    )

    fea = makeFeatures(instance, master, opts, glyphOrder)
    fb.addOpenTypeFeatures(fea)

    palettes = font.customParameters["Color Palettes"]
    palettes = [[tuple(v / 255 for v in c) for c in p] for p in palettes]
    fb.setupCPAL(palettes)
    fb.setupCOLR(colorLayers)

    instance.font = fb.font
    if opts.debug:
        fb.font.save(f"{instance.fontName}.otf")

    return fb.font


def buildVF(opts):
    font = GSFont(opts.glyphs)
    glyphOrder = [g.name for g in font.glyphs]

    for instance in font.instances:
        print(f" MASTER  {instance.name}")
        build(instance, opts, glyphOrder)
        if instance.name == "Regular":
            regular = instance

    ds = DesignSpaceDocument()

    for i, axisDef in enumerate(font.axes):
        axis = ds.newAxisDescriptor()
        axis.tag = axisDef.axisTag
        axis.name = axisDef.name
        axis.hidden = axisDef.hidden
        axis.maximum = max(x.axes[i] for x in font.instances)
        axis.minimum = min(x.axes[i] for x in font.instances)
        axis.default = regular.axes[i]
        ds.addAxis(axis)

    for instance in font.instances:
        source = ds.newSourceDescriptor()
        source.font = instance.font
        source.familyName = instance.familyName
        source.styleName = instance.name
        source.name = instance.fullName
        source.location = {a.name: instance.axes[i] for i, a in enumerate(ds.axes)}
        ds.addSource(source)

    print(f" MERGE   {font.familyName}")
    otf, _, _ = merge(ds)
    return otf


def main():
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Build Rana Kufi.")
    parser.add_argument("glyphs", help="input Glyphs source file", type=Path)
    parser.add_argument("version", help="font version")
    parser.add_argument("otf", help="output OTF file", type=Path)
    parser.add_argument("--debug", help="Save debug files", action="store_true")
    args = parser.parse_args()

    otf = buildVF(args)
    otf.save(args.otf)


main()
