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

import csv
import json

import uharfbuzz as hb


def parsefeatures(text):
    features = {}
    for fea in text.split(","):
        if "=" in fea:
            fea, val = fea.split("=")
            features[fea] = int(val)
        else:
            features[fea] = True
    return features


def shape(font, text, direction, script, language, features, variations):
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.direction = direction
    buffer.script = script
    if language:
        buffer.language = language

    old_variations = font.get_var_coords_normalized()
    if variations:
        font.set_variations(variations)

    hb.shape(font, buffer, features)

    output = []
    for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions):
        glyph = font.glyph_to_string(info.codepoint)
        glyph += f"={info.cluster}"
        if pos.x_offset or pos.y_offset:
            glyph += f"@{pos.x_offset},{pos.y_offset}"
        glyph += f"+{pos.x_advance}"
        if pos.y_advance:
            glyph += f",{pos.y_advance}"
        output.append(glyph)

    if variations:
        font.set_var_coords_normalized(old_variations)

    return "|".join(output)


def open_font(path):
    blob = hb.Blob.from_file_path(path)
    face = hb.Face(blob)
    font = hb.Font(face)
    return font


def main(args):
    fonts = [open_font(f) for f in args.font]
    tests = []
    with open(args.csv) as f:
        reader = csv.DictReader(f, delimiter=";", lineterminator="\n")
        for test in reader:
            test = {k: v for k, v in test.items() if v}
            if features := test.get("features"):
                test["features"] = parsefeatures(features)
            if variations := test.get("variations"):
                test["variations"] = parsefeatures(variations)
            test["expectation"] = {
                ("default" if i == 0 else path.name): shape(
                    font,
                    test.get("input"),
                    test.get("direction", "rtl"),
                    test.get("script", "arab"),
                    test.get("language"),
                    test.get("features"),
                    test.get("variations"),
                )
                for i, (path, font) in enumerate(zip(args.font, fonts))
            }

            tests.append(test)

    doc = {
        "configuration": {
            "defaults": {
                "script": "arab",
                "direction": "rtl",
            },
        },
        "tests": tests,
    }

    args.json.write_text(json.dumps(doc, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("json", type=Path, help="output .json file path.")
    parser.add_argument("csv", type=Path, help="input .csv file path.")
    parser.add_argument("font", type=Path, nargs="+", help="font to update with.")

    args = parser.parse_args()
    main(args)
