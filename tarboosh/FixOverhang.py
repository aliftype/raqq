"""
Bari Ye Processing
------------------

This plugin provides some verbs which are extremely useful for handling the
bari-ye sequence in the Nastaliq script, but which require a certain amount
of set-up in advance from the user.

This plugin provides the following verbs:

``FixOverhang`` takes two integer values; an additional number of points to
separate the end of overhanging glyphs and the following glyph, and the
adjustment threshold (any adjustments less than the threshold will be dropped),
and a glyph class for the overhanging glyphs to be adjusted, and two glyph
classes for initials and medials, and computes rules which act only on short
sequences; it evaluates all possible short sequences (using width-binning to
keep the number of combinations to a reasonable number), computes the total
width of each sequence, compares this against the negative RSB of the
overhanging glyphs, and emits appropriate kerning rules to generate the desired
separation. e.g. ``FixOverhang 10 100 @hanging @medials @initials`` will
ensure that there are at least 10 points between the end of the tail of each
glyph in ``@overhanging`` and any `@medials`/`@initials` glyph preceding the
sequence, and will drop any adjustment bellow 100.
"""


import fontFeatures
from glyphtools import categorize_glyph, get_glyph_metrics, bin_glyphs_by_metric
import warnings

from fez import FEZVerb

PARSEOPTS = dict(use_helpers=True)

GRAMMAR = ""

BYMoveDots_GRAMMAR = """
?start: action
action: STRATEGY glyphselector
STRATEGY: "AlwaysDrop" | "TryToFit"
"""

FixOverhang_GRAMMAR = """
?start: action
action: integer_container integer_container glyphselector glyphselector glyphselector
"""

VERBS = ["FixOverhang"]


failsafe_max_length = 4
failsafe_min_run = 100


class FixOverhang(FEZVerb):
    def action(self, args):
        parser = self.parser

        overhang_padding, adjustment_threshold, glyphs, medis, inits = args
        overhang_padding = overhang_padding.resolve_as_integer()
        adjustment_threshold = adjustment_threshold.resolve_as_integer()
        overhangers = glyphs.resolve(parser.fontfeatures, parser.font)
        medis = medis.resolve(parser.fontfeatures, parser.font)
        inits = inits.resolve(parser.fontfeatures, parser.font)

        binned_medis = bin_glyphs_by_metric(parser.font, medis, "run", bincount=8)
        binned_inits = bin_glyphs_by_metric(parser.font, inits, "run", bincount=8)
        rules = []
        maxchainlength = 0
        longeststring = []
        for yb in overhangers:
            entry_anchor = parser.fontfeatures.anchors[yb]["entry"]
            overhang = max(
                -get_glyph_metrics(parser.font, yb)["rsb"],
                get_glyph_metrics(parser.font, yb)["xMax"] - entry_anchor[0],
            )

            workqueue = [[x] for x in binned_inits]
            while workqueue:
                string = workqueue.pop(0)
                totalwidth = sum([max(x[1], failsafe_min_run) for x in string])
                if totalwidth > overhang or len(string) > failsafe_max_length:
                    continue

                adjustment = overhang - totalwidth + int(overhang_padding)
                if (
                    adjustment_threshold is not None
                    and adjustment < adjustment_threshold
                ):
                    continue
                postcontext = [x[0] for x in string[:-1]] + [[yb]]
                input_ = string[-1]
                example = [input_[0][0]] + [x[0] for x in postcontext]
                warnings.warn(
                    f"For glyphs in {example}, {overhang=} {totalwidth=} {adjustment=}"
                )
                maxchainlength = max(maxchainlength, len(string))

                rules.append(
                    fontFeatures.Positioning(
                        [input_[0]],
                        [fontFeatures.ValueRecord(xAdvance=int(adjustment))],
                        postcontext=postcontext,
                    )
                )
                for medi in binned_medis:
                    workqueue.append([medi] + string)
        warnings.warn(
            f"Bari Ye collision maximum chain length was {maxchainlength} glyphs"
        )
        return [fontFeatures.Routine(rules=rules, flags=8)]
