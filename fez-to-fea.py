from fez import FezParser
from fontFeatures.optimizer import Optimizer
from babelfont import load
from pathlib import Path
import warnings


def fez2fea(args):
    font = load(str(args.font))
    parser = FezParser(font)
    parser.parseFile(args.fez)
    Optimizer(parser.fontfeatures).optimize(level=args.O)

    with open(args.output, "w") as output:
        output.write(parser.fontfeatures.asFea(do_gdef=args.gdef))

    if parser.font_modified:
        modified = f"modified-{args.font.name}"
        parser.font.save(modified)
        warnings.warn(f"Modified font written on {modified}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "-O", nargs="?", const=1, type=int, default=0, help="Optimization level"
    )
    parser.add_argument(
        "--gdef",
        action="store_true",
        help="Don't add a GDEF table to output",
    )
    parser.add_argument("-v", "--verbose", help="Print verbose output")
    parser.add_argument("-o", "--output", type=Path, help="Output path")
    parser.add_argument(
        "font", type=Path, help="Font file (.glyphs) to process", metavar="FONT"
    )
    parser.add_argument(
        "fez", type=Path, help="FEZ file to process", metavar="FEZ", nargs="?"
    )

    args = parser.parse_args()

    with warnings.catch_warnings():
        if not args.verbose:
            warnings.simplefilter("ignore")
        fez2fea(args)


if __name__ == "__main__":
    main()
