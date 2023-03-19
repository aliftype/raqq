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
from glyphsLib import GSFont


def main(rags):
    doc = toml.load(args.toml)
    configuration = doc["configuration"]

    font = GSFont(args.glyphs)

    forbidden_glyphs = ["kashida-ar"]
    for glyph in font.glyphs:
        if glyph.color == 0:
            forbidden_glyphs.append(glyph.name)

    configuration["forbidden_glyphs"] = forbidden_glyphs

    args.toml.write_text(toml.dumps(doc))


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("toml", type=Path, help="input .toml file path.")
    parser.add_argument("glyphs", type=Path, help="input .glyphs file path.")

    args = parser.parse_args()
    main(args)
