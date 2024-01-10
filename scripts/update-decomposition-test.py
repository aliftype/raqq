#!/usr/bin/env python3
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

import json

import uharfbuzz as hb
from glyphsLib import GSFont


def main(args):
    font = GSFont(args.glyphs)

    forbidden_glyphs = []
    for glyph in font.glyphs:
        if glyph.color == 0:
            forbidden_glyphs.append(glyph.name)

    blob = hb.Blob.from_file_path(args.font)
    face = hb.Face(blob)
    unicodes = face.unicodes
    tests = []
    for u in unicodes:
        c = chr(u)
        if c.isalpha():
            test = {"input": f"{c} {c}\u200D \u200D{c}\u200D \u200D{c}"}
            tests.append(test)

    doc = {
        "configuration": {
            "defaults": {
                "script": "arab",
                "direction": "rtl",
            },
            "forbidden_glyphs": forbidden_glyphs,
        },
        "tests": tests,
    }

    args.json.write_text(json.dumps(doc, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("json", type=Path, help="output .json file path.")
    parser.add_argument("glyphs", type=Path, help="input .glyphs file path.")
    parser.add_argument("font", type=Path, help="input .ttf file path.")

    args = parser.parse_args()
    main(args)
