# Copyright (c) 2020-2024 Khaled Hosny
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

import datetime
import os
from xml.etree import ElementTree as etree

from fontTools.cu2qu.ufo import glyphs_to_quadratic
from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.transform import Identity, Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables._h_e_a_d import mac_epoch_diff
from fontTools.varLib import build_many as merge
from glyphsLib import GSAnchor, GSFont, GSFontMaster, GSLayer
from glyphsLib.builder.tokens import TokenExpander
from glyphsLib.glyphdata import GlyphData
from glyphsLib.glyphdata import get_glyph as getGlyphInfo

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

# Monkey patch GSLayer


def axesToStr(axes):
    return "{" + ", ".join(f"{a:g}" for a in axes) + "}"


# glyphs_to_quadratic expects a UFO layer with clearContours, so give GSLayer
# one.
def GSLayer_clearContours(self):
    self.paths = []


def GSLayer__repr__(self: GSLayer):
    name = []
    if self.layerId == self.associatedMasterId:
        name.append(self.parent.parent.masters[self.layerId].name)
    if color := self.attributes.get("colorPalette"):
        name.append(f"Color {color}")
    if self.layerId != self.associatedMasterId and (
        coords := self.attributes.get("coordinates")
    ):
        name.append(axesToStr(coords))
    if name:
        name = " ".join(name)
    else:
        name = self.name
    if self.parent:
        parent = self.parent.name
    else:
        parent = "orphan"
    return f'<GSLayer "{name}" ({parent})>'


GSLayer.clearContours = GSLayer_clearContours
GSLayer.__repr__ = GSLayer__repr__


def draw(layer, glyphSet):
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

    pen = TTGlyphPointPen(glyphSet)
    layer.drawPoints(pen)

    return pen.glyph()


def makeKern(font, master):
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


def getAnchorPos(font, glyph, default, name):
    coords = font.masters[default.layerId].axes
    pos = [(coords, default.anchors[name].position)]
    for master in font.masters:
        if (layer := glyph.layers[master.id]) is not None:
            coords = master.axes
            pos.append((master.axes, layer.anchors[name].position))

    x = []
    y = []
    axes = [a.axisTag for a in font.axes]
    for coords, position in pos:
        loc = ",".join(f"{axes[i]}={c}" for i, c in enumerate(coords))
        x.append(f"{loc}:{position.x}")
        y.append(f"{loc}:{position.y}")

    return f"({' '.join(x)})", f"({' '.join(y)})"


def makeMark(font, glyphOrder):
    classes = ""
    mark2base = {}
    mark2liga = ""

    ligatures = {}

    for gname in glyphOrder:
        glyph = font.glyphs[gname]
        if glyph is None:
            continue

        if (glyph.category, glyph.subCategory) == ("Letter", "Ligature"):
            ligatures[gname] = {i + 1: [] for i in range(gname.count("_") + 1)}

        layer = glyph.layers[0]
        for anchor in layer.anchors:
            name = anchor.name
            x, y = getAnchorPos(font, glyph, layer, name)
            if name.startswith("_"):
                classes += f"markClass {gname} <anchor {x} {y}> @mark_{name[1:]};\n"
            elif not name[0].isalpha():
                continue
            elif name.startswith("caret_") or name in ("exit", "entry"):
                continue
            elif "_" in name:
                name, index = name.split("_")
                ligatures[gname][int(index)].append((name, (x, y)))
            else:
                mark2base.setdefault(name, "")
                mark2base[
                    name
                ] += f"pos base {gname} <anchor {x} {y}> mark @mark_{name};\n"

    for name, components in ligatures.items():
        mark2liga += f"pos ligature {name}"
        for component, anchors in components.items():
            if component != 1:
                mark2liga += " ligComponent"
            for anchor, (x, y) in anchors:
                mark2liga += f" <anchor {x} {y}> mark @mark_{anchor}"
        mark2liga += ";\n"

    base = ""
    for name, code in mark2base.items():
        base += f"""
lookup mark2base_{name} {{
lookupflag 0;
{code}
}} mark2base_{name};
"""

    return f"""
{classes}
{base}
lookup mark2liga_auto {{
lookupflag 0;
{mark2liga}
}} mark2liga_auto;
"""


def makeCurs(font, glyphOrder):
    fea = ""

    exit_ = {}
    entry_ = {}

    for gname in glyphOrder:
        glyph = font.glyphs[gname]
        if glyph is None:
            continue

        layer = glyph.layers[0]
        for anchor in layer.anchors:
            name = anchor.name
            x, y = getAnchorPos(font, glyph, layer, name)
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


LANG_IDS = {"ARA": "0x0C01", "ENG": "0x0409"}


def makeFeatures(font, master, args, glyphOrder):
    expander = TokenExpander(font, master)

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
        code = expander.expand(code)
        fea += f"@{name} = [{code}];\n"

    for prefix in font.featurePrefixes:
        if prefix.disabled:
            continue
        code = expander.expand(prefix.code)
        fea += code + "\n"

    for feature in font.features:
        if feature.disabled:
            continue
        code = expander.expand(feature.code)
        names = ""
        for label in feature.labels:
            names += f'name 3 1 {LANG_IDS[label["language"]]} "{label["value"]}";\n'
        if names:
            code = "featureNames { " + names + " };\n" + code

        if "# Automatic Code\n" in code:
            before, after = code.split("# Automatic Code\n", 1)
            if feature.name == "mark":
                auto = makeMark(font, glyphOrder)
            elif feature.name == "curs":
                auto = makeCurs(font, glyphOrder)
            elif feature.name == "kern":
                auto = makeKern(font, master)
            else:
                raise ValueError(
                    f"Unknown feature for “# Automatic Code”: {feature.name}"
                )
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
            layer = glyph.layers[0]
            for anchor in layer.anchors:
                if anchor.name.startswith("_"):
                    marks.add(name)
                elif anchor.name.startswith("caret_"):
                    ligatures.add(name)

        layer = glyph.layers[0]
        caret = ""
        for anchor in layer.anchors:
            if anchor.name.startswith("caret_"):
                _, index = anchor.name.split("_")
                if not caret:
                    caret = f"LigatureCaretByPos {name}"
                x, _ = getAnchorPos(font, glyph, layer, anchor.name)
                caret += f" {x}"
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
            if prop._localized_values:
                return {k[:2].lower(): v for (k, v) in prop._localized_values.items()}
            return prop.value


XLINK = "http://www.w3.org/1999/xlink"
HREF = f"{{{XLINK}}}href"


def ntos(n):
    n = round(n, 2)
    s = str(int(n) if round(n) == n else n)
    if s.startswith("0."):
        s = s[1:]
    if s.startswith("-0."):
        s = "-" + s[2:]
    return s


def drawSVG(font, glyphSet, name, defs):
    gid = f"g{font.getGlyphID(name)}"
    if (elem := defs.find(f"*[@id='{gid}']")) is None:
        pen = SVGPen(font, defs, glyphSet)
        glyphSet[name].draw(pen)

        elem = pen.finish()
        elem.attrib["id"] = gid
    return elem


class SVGPen(SVGPathPen):
    def __init__(self, font, defs, glyphSet):
        super().__init__(glyphSet, ntos=ntos)
        self.font = font
        self.defs = defs
        self.components = []

    def addComponent(self, glyphName, transformation):
        self.components.append((glyphName, transformation))

    def finish(self):
        font = self.font
        defs = self.defs
        glyphSet = self.glyphSet

        g = None
        path = None
        commands = self.getCommands()
        components = self.components
        if components:
            if len(components) == 1 and not commands:
                g = defs
            else:
                g = etree.SubElement(defs, "g")
            for name, transform in components:
                elem = drawSVG(font, glyphSet, name, defs)
                use = etree.SubElement(g, "use")
                use.attrib[HREF] = "#" + elem.attrib["id"]
                if transform != Identity:
                    if transform[:4] == (1, 0, 0, 1):
                        dx, dy = transform[4:]
                        transform = f"translate({dx}, {dy})"
                    else:
                        matrix = ",".join(ntos(t) for t in transform)
                        transform = f"matrix({matrix})"
                    use.attrib["transform"] = transform
            if g == defs:
                g = use

        if commands:
            path = etree.SubElement(g if g is not None else defs, "path")
            path.attrib["d"] = commands

        return g if g is not None else path


def addSVG(fb):
    font = fb.font
    SVG = font["SVG "] = newTable("SVG ")
    SVG.compressed = True
    SVG.docList = []

    COLR = font["COLR"]
    CPAL = font["CPAL"]

    etree.register_namespace("x", XLINK)
    root = etree.Element("svg", {"xmlns": "http://www.w3.org/2000/svg"})
    defs = etree.SubElement(root, "defs")

    gids = [font.getGlyphID(name) for name in COLR.ColorLayers]
    assert gids == list(range(min(gids), max(gids) + 1))

    glyphSet = font.getGlyphSet()
    for name, layers in COLR.ColorLayers.items():
        gid = font.getGlyphID(name)
        g = etree.SubElement(root, "g")
        g.attrib["id"] = f"glyph{gid}"
        g.attrib["transform"] = "scale(1,-1)"
        for layer in layers:
            elem = drawSVG(font, glyphSet, layer.name, defs)

            color = CPAL.palettes[0][layer.colorID]
            use = etree.SubElement(g, "use")
            use.attrib[HREF] = "#" + elem.attrib["id"]
            use.attrib["fill"] = color.hex()[:7]
            if color.alpha != 255:
                use.attrib["opacity"] = ntos(color.alpha / 255)

    etree.indent(root)
    doc = etree.tostring(root)
    SVG.docList.append((doc, min(gids), max(gids)))


def buildMaster(font, master, args):
    colorLayers = {}

    glyphSet = {}
    for name in font.glyphOrder:
        glyph = font.glyphs[name]
        if glyph is None:
            return

        layer = glyph.layers[master.id]
        if layer is None:
            continue

        glyphSet[name] = layer

        for layer in glyph.layers:
            if layer.associatedMasterId != master.id:
                continue
            paletteIdx = layer.attributes.get("colorPalette", None)
            if paletteIdx is None:
                continue
            colorLayers.setdefault(name, [])
            if layer.layerId != master.id:
                layer.name = f"{name}.color{len(colorLayers[name])}"
                glyphSet[layer.name] = layer
                colorLayers[name].append((layer.name, paletteIdx))
            else:
                colorLayers[name].append((name, paletteIdx))

    colorGlyphs = list(colorLayers.keys())
    allGlyphs = font.glyphOrder + list(glyphSet.keys())

    def key(name):
        if name in colorGlyphs:
            return len(allGlyphs) + colorGlyphs.index(name)
        return allGlyphs.index(name)

    glyphOrder = sorted(glyphSet.keys(), key=key)

    fb = FontBuilder(font.upm, isTTF=True)
    fb.setupGlyphOrder(glyphOrder)

    glyphs = {}
    for name, layer in glyphSet.items():
        glyphs[name] = draw(layer, glyphSet)

    fb.setupGlyf(glyphs)

    metrics = {}
    glyf = fb.font["glyf"]
    for name, glyph in glyphs.items():
        metrics[name] = (glyphSet[name].width, glyph.xMin)
    fb.setupHorizontalMetrics(metrics)

    # Add empty name table, varLib merger needs one for fvar names
    fb.setupNameTable({}, mac=False)

    if colorLayers:
        from glyphsLib.builder.common import to_ufo_color

        palettes = font.customParameters["Color Palettes"]
        palettes = [[to_ufo_color(c) for c in p] for p in palettes]
        paletteTypes = None
        if len(palettes) == 2:
            paletteTypes = [0x0001, 0x0002]
        fb.setupCPAL(palettes, paletteTypes=paletteTypes)
        fb.setupCOLR(colorLayers)

    return fb.font


def buildBase(font, instance, vf, args):
    master = font.masters[0]

    characterMap = {}
    for name in font.glyphOrder:
        glyph = font.glyphs[name]
        for uni in glyph.unicodes:
            characterMap[int(uni, 16)] = glyph.name

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

    fb = FontBuilder(font=vf)
    date = font.date.replace(tzinfo=datetime.timezone.utc)
    stat = args.input.stat()
    fb.updateHead(
        fontRevision=version,
        created=int(date.timestamp()) - mac_epoch_diff,
        modified=int(stat.st_mtime) - mac_epoch_diff,
    )
    fb.setupCharacterMap(characterMap)

    fb.setupHorizontalHeader(
        ascent=master.customParameters["hheaAscender"],
        descent=master.customParameters["hheaDescender"],
        lineGap=master.customParameters["hheaLineGap"] or 0,
    )

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
        achVendID=font.properties["vendorID"],
        fsType=calcBits(font.customParameters["fsType"], 0, 16),
        fsSelection=calcFsSelection(instance),
        ulUnicodeRange1=calcBits(font.customParameters["unicodeRanges"], 0, 32),
        ulCodePageRange1=calcBits(codePages, 0, 32),
    )

    vf_names = [n for n in vf["name"].names if n.platformID == 3]
    fb.setupNameTable(names, mac=False)
    fb.font["name"].names += vf_names

    fb.font.cfg["fontTools.otlLib.builder:WRITE_GPOS7"] = True

    fea = makeFeatures(font, master, args, font.glyphOrder)
    feapath = args.input
    if os.environ.get("FONTTOOLS_LOOKUP_DEBUGGING"):
        feapath = feapath.with_suffix(".fea")
        with open(feapath, "w") as f:
            f.write(fea)
        font.save(feapath.with_suffix(".debug.glyphs"))
    fb.addOpenTypeFeatures(fea, filename=feapath)

    if not args.no_SVG:
        addSVG(fb)

    return fb.font


def propagateAnchors(glyph, layer):
    if glyph is not None and glyph.color == 0:
        return

    if layer.layerId != layer.associatedMasterId:
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


def removeOverlap(font, layer):
    from pathops import Path

    if not layer.paths:
        return

    glyphSet = {}
    if layer.layerId == layer.associatedMasterId:
        glyphSet = {g.name: g.layers[layer.layerId] for g in font.glyphs}

    path = Path()
    layer.draw(path.getPen(glyphSet=glyphSet))
    path.simplify(fix_winding=True, keep_starting_points=True)
    layer.paths = []
    path.draw(layer.getPen())


def prepare(args):
    font = GSFont(args.input)
    instance = font.instances[0]  # XXX

    font.glyphOrder = [g.name for g in font.glyphs if g.export]

    # Add masters for all intermediate layers
    coordinates = set()
    for name in font.glyphOrder:
        glyph = font.glyphs[name]
        for layer in glyph.layers:
            if coords := layer.attributes.get("coordinates"):
                coordinates.add(tuple(coords))

    index = len(font.masters)
    for axes in coordinates:
        master = GSFontMaster()
        master.axes = list(axes)
        master.metrics = list(font.metrics)
        master.customParameters = font.masters[0].customParameters
        master.xHeight = font.masters[0].xHeight
        master.capHeight = font.masters[0].capHeight
        master.id = f"m{index + 1:02}"
        master.name = f"master_{axesToStr(axes)}"
        for name in font.glyphOrder:
            glyph = font.glyphs[name]
            for layer in glyph.layers:
                if layer.attributes.get("coordinates") == master.axes:
                    layer.associatedMasterId = master.id
                    if len(layer.attributes) == 1:
                        layer.layerId = master.id
                    del layer.attributes["coordinates"]

        # we are not using masters.append() because it adds layer for the new
        # master to each glyph in the font.
        font.masters.insert(index, master)
        index += 1

    for name in font.glyphOrder:
        glyph = font.glyphs[name]
        # Set categories from the external GlyphGata file
        with open(args.data) as f:
            data = GlyphData.from_files(f)
        info = getGlyphInfo(glyph.name, data=data)
        if glyph.category is None:
            glyph.category = info.category
        if glyph.subCategory is None:
            glyph.subCategory = info.subCategory

        for layer in glyph.layers:
            if glyph.color == 0:
                # Clear placeholder glyphs
                layer.components = []
                layer.width = 600
            elif (glyph.category, glyph.subCategory) == ("Mark", "Nonspacing"):
                # Zero mark width
                layer.width = 0
                if origin := layer.anchors["*origin"]:
                    for path in layer.paths:
                        path.applyTransform([1, 0, 0, 1, -origin.position.x, 0])
                    for component in layer.components:
                        x = component.position.x - origin.position.x
                        y = component.position.y
                        component.position = (x, y)
            propagateAnchors(glyph, layer)

        # Group layers by master, so we can convert corresponding layers from all
        # masters together.
        groups = []
        for master in font.masters:
            if layers := [l for l in glyph.layers if l.associatedMasterId == master.id]:
                groups.append(layers)

        # Convert interpolatable layers together.
        for layers in zip(*groups):
            if len(layers) == 1:
                # No interpolation needed, we can safely remove overlaps
                removeOverlap(font, layers[0])
            glyphs_to_quadratic(layers, max_err=1.0, reverse_direction=True)

    return font, instance


def build(font, default_instance, args):
    ds = DesignSpaceDocument()

    axisNames = {
        "MSHQ": {"ar": "مشق"},
        "SPAC": {"ar": "مسافات"},
    }

    axisMappings = font.customParameters["Axis Mappings"]
    for axis, default in zip(font.axes, default_instance.axes):
        locations = axisMappings[axis.axisTag].values()
        ds.addAxisDescriptor(
            name=axis.name,
            tag=axis.axisTag,
            labelNames={"en": axis.name, **axisNames.get(axis.axisTag, {})},
            hidden=axis.hidden,
            maximum=max(locations),
            minimum=min(locations),
            default=default,
        )

    for i, master in enumerate(font.masters):
        ds.addSourceDescriptor(
            name=f"master_{i}",
            font=buildMaster(font, master, args),
            familyName=font.familyName,
            styleName=master.name,
            location={a.name: master.axes[i] for i, a in enumerate(ds.axes)},
        )

    for i, instance in enumerate(font.instances):
        location = {a.name: instance.axes[i] for i, a in enumerate(ds.axes)}
        ds.addLocationLabelDescriptor(name=instance.name, userLocation=location)
        ds.addInstanceDescriptor(
            name=f"instance_{i}",
            familyName=font.familyName,
            localisedStyleName={"en": instance.name},
            postScriptFontName=instance.fontName,
            location=location,
        )

    mappings = [
        [{"Justification": -100}, {"Spacing": -100, "Mashq": 0}],
        [{"Justification": -50}, {"Spacing": 0, "Mashq": 0}],
        [{"Justification": 0}, {"Spacing": 0, "Mashq": 10}],
        [{"Justification": 90}, {"Spacing": 0, "Mashq": 100}],
        [{"Justification": 100}, {"Spacing": 125, "Mashq": 100}],
    ]

    for input, output in mappings:
        ds.addAxisMappingDescriptor(inputLocation=input, outputLocation=output)

    vf = merge(ds)["VF"]
    if "ltag" in vf:
        del vf["ltag"]

    otf = buildBase(font, default_instance, vf, args)
    return otf


def main():
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Build Raqq font.")
    parser.add_argument("input", help="input Glyphs source file", type=Path)
    parser.add_argument("version", help="font version", type=str)
    parser.add_argument("output", help="output OTF file", type=Path)
    parser.add_argument("--data", help="GlyphData.xml file", type=Path)
    parser.add_argument("--no-SVG", help="do not build SVG table", action="store_true")
    args = parser.parse_args()

    font, instance = prepare(args)
    otf = build(font, instance, args)
    otf.save(args.output)


main()
