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

import toml
import json
import uharfbuzz as hb


def shape(font, text, direction, script, language, features):
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.direction = direction
    buffer.script = script
    if language:
        buffer.language = language

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

    return "|".join(output)


def open_font(path):
    blob = hb.Blob.from_file_path(path)
    face = hb.Face(blob)
    font = hb.Font(face)
    return font


def update_shaping_tests(doc, fonts, default):
    configuration = doc["configuration"]

    defaults = configuration["defaults"]
    direction = defaults["direction"]
    script = defaults["script"]
    language = defaults.get("language")
    features = defaults.get("features")

    tests = doc["tests"]
    for test in tests:
        expectation = {}
        for path in fonts:
            name = "default" if path.stem == default else path.name
            expectation[name] = shape(
                fonts[path],
                test.get("input"),
                test.get("direction", direction),
                test.get("script", script),
                test.get("language", language),
                test.get("features", features),
            )
        test["expectation"] = expectation


def update_decomposition_tests(doc, fonts, default):
    configuration = doc["configuration"]

    defaults = configuration["defaults"]
    direction = defaults["direction"]
    script = defaults["script"]
    language = defaults.get("language")
    features = defaults.get("features")

    tests = doc.setdefault("tests", [])

    for path in fonts:
        if path.stem != default:
            continue

        font = fonts[path]
        unicodes = font.face.unicodes
        for u in unicodes:
            c = chr(u)
            if c.isalpha():
                test = {"input": f"{c} {c}\u200D \u200D{c}\u200D \u200D{c}"}
                tests.append(test)


def main(rags):
    doc = toml.load(args.toml)
    configuration = doc.setdefault("configuration", {})
    defaults = configuration.setdefault("defaults", {})
    defaults.setdefault("direction", "rtl")
    defaults.setdefault("script", "arab")

    fonts = {f: open_font(f) for f in args.fonts}

    if "forbidden_glyphs" in configuration:
        update_decomposition_tests(doc, fonts, args.default)
    else:
        update_shaping_tests(doc, fonts, args.default)

    args.json.write_text(json.dumps(doc, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("json", type=Path, help="output .json file path.")
    parser.add_argument("default", help="default font’s file name")
    parser.add_argument("toml", type=Path, help="input .toml file path.")
    parser.add_argument("fonts", nargs="+", type=Path, help="fonts to update with.")

    args = parser.parse_args()
    main(args)
