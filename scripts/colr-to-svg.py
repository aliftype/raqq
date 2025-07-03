from fontTools.ttLib import TTFont, newTable
from fontTools.pens.svgPathPen import SVGPathPen
from xml.etree import ElementTree as ET


def convert(font):
    COLR = font["COLR"]
    CPAL = font["CPAL"]
    SVG_ = font["SVG "] = newTable("SVG ")
    SVG_.compressed = True

    SVG_.docList = []

    glyphSet = font.getGlyphSet()
    palette = CPAL.palettes[0]

    for name, layers in COLR.ColorLayers.items():
        gid = font.getGlyphID(name)

        doc = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", version="1.1")
        g = ET.SubElement(doc, "g", id=f"glyph{gid}", transform="scale(1,-1)")

        for layer in layers:
            pen = SVGPathPen(glyphSet)
            glyphSet[layer.name].draw(pen)

            path = ET.SubElement(g, "path", d=pen.getCommands())
            if layer.colorID != 0xFFFF:
                color = palette[layer.colorID]
                path.attrib["fill"] = color.hex()[:7]
                if color.alpha != 255:
                    path.attrib["opacity"] = str(color.alpha / 255)
            else:
                path.attrib["fill"] = "currentColor"
        ET.indent(doc)
        SVG_.docList.append((ET.tostring(doc), gid, gid))


def main():
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Convert COLR/CPAL tables to SVG")
    parser.add_argument("font", type=Path, help="Font file")

    args = parser.parse_args()
    font = TTFont(args.font)
    convert(font)
    font.save(args.font)


if __name__ == "__main__":
    main()
