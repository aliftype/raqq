#!/usr/bin/env python3
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

import uharfbuzz as hb
import itertools


THRESHOLD = 50
OVERHANGERS = ["ح", "ح\u200D", "ے"]
DUAL_JOINERS = ["ٮ", "ح", "س", "ص", "ط", "ع", "ڡ", "ك", "ل", "م", "ه"]

BUFFER = hb.Buffer()


def shape(font, text, direction="rtl", script="arab", features=None):
    BUFFER.clear_contents()
    BUFFER.add_str(text)
    BUFFER.direction = direction
    BUFFER.script = script
    BUFFER.flags = hb.BufferFlags.REMOVE_DEFAULT_IGNORABLES

    hb.shape(font, BUFFER, features)

    infos = BUFFER.glyph_infos
    positions = BUFFER.glyph_positions
    if BUFFER.direction == "rtl":
        infos.reverse()
        positions.reverse()

    glyphs = []
    advance = 0
    for info, pos in zip(infos, positions):
        glyph = font.glyph_to_string(info.codepoint)
        glyphs.append(glyph)
        advance += pos.x_advance

    overhang = font.get_glyph_h_advance(infos[-1].codepoint)
    adjustment = overhang - advance

    return glyphs, adjustment


def open_font(path):
    blob = hb.Blob.from_file_path(path)
    face = hb.Face(blob)
    font = hb.Font(face)
    return font


def main(args):
    font = open_font(args.font)

    rules = []
    for overhanger in OVERHANGERS:
        i = 0
        while True:
            sequence = [DUAL_JOINERS] + [DUAL_JOINERS] * i + [[overhanger]]
            found = False
            for string in itertools.product(*sequence):
                text = "".join(string)
                glyphs, adjustment = shape(font, text, features={"kern": False})
                if adjustment < THRESHOLD:
                    continue
                found = True

                match = glyphs[0]
                lookahead = glyphs[1:]
                rules.append(f"\tpos {match}' {adjustment} {' '.join(lookahead)};")
            if not found:
                break
            i += 1

    with open(args.fea, "w") as fea:
        fea.write("# THIS FILE IS AUTO GENERATED, DO NOT EDIT\n\n")
        fea.write("lookup overhang {\n")
        fea.write("  lookupflag IgnoreMarks;\n")
        fea.write("\n".join(rules))
        fea.write("\n} overhang;\n\n")


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("font", type=Path, help="input font file path.")
    parser.add_argument("fea", type=Path, help="output .fea file path.")

    args = parser.parse_args()
    main(args)
