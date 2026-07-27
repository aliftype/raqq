#!/usr/bin/env python3
# Copyright (c) 2020-2026 Khaled Hosny
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

from fontTools.ttLib import TTFont

AXIS_NAMES = {
    "MSHQ": {0x0C01: "مشق"},
    "SPAC": {0x0C01: "مسافات"},
}


def name_axes(font):
    name = font["name"]
    fvar = font["fvar"]
    if len(fvar.axes) > len(AXIS_NAMES):
        raise KeyError(
            f"The font has {len(fvar.axes)} axes,"
            " expected maximum of {len(AXIS_NAMES)} axes"
        )
    for axis in fvar.axes:
        for language, string in AXIS_NAMES.get(axis.axisTag, {}).items():
            name.setName(string, axis.axisNameID, 3, 1, language)


PALETTE_TYPES = [0x0001, 0x0002]


def type_palettes(font):
    cpal = font["CPAL"]
    if len(cpal.palettes) != len(PALETTE_TYPES):
        raise KeyError(
            f"The font has {len(cpal.palettes)} palettes,"
            f" expected {len(PALETTE_TYPES)} palettes"
        )
    cpal.version = 1
    cpal.paletteTypes = list(PALETTE_TYPES)
    cpal.paletteLabels = [cpal.NO_NAME_ID] * len(cpal.palettes)
    cpal.paletteEntryLabels = [cpal.NO_NAME_ID] * cpal.numPaletteEntries


def main():
    parser = argparse.ArgumentParser(description="Post-process Raqq fonts.")
    parser.add_argument("input", metavar="FILE", help="input font to process")
    parser.add_argument("output", metavar="FILE", help="output font to write")
    args = parser.parse_args()

    font = TTFont(args.input)
    name_axes(font)
    type_palettes(font)
    font.save(args.output)


if __name__ == "__main__":
    main()
