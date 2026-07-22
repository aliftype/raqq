# Copyright (c) 2020-2025 Khaled Hosny
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

NAME = Raqq

SHELL = bash
MAKEFLAGS := -sr
PYTHON := venv/bin/python3

SOURCEDIR = sources
SCRIPTDIR = scripts
FONTDIR = fonts
TESTDIR = tests

NAMES = ${NAME} ${NAME}Sura
FONTS = ${NAMES:%=${FONTDIR}/%.ttf}

JSON = ${TESTDIR}/shaping.json
HTML = ${NAMES:%=${TESTDIR}/%-shaping.html}
SVG = FontSample.svg

GLYPHSFILES = ${NAMES:%=${SOURCEDIR}/%.glyphspackage}

TAG = $(shell git describe --tags --abbrev=0)
VERSION = ${TAG:v%=%}
DIST = ${NAME}-${VERSION}


.SECONDARY:
.ONESHELL:
.PHONY: all clean dist ttf test doc

all: ttf doc
ttf: ${FONTS}
test: ${HTML}
expectation: ${JSON}

update-fea: ${FONTS}
	fonts=(${FONTS})
	glyphsfiles=(${GLYPHSFILES})
	for i in $${!fonts[@]}; do
		echo "  GEN    $${glyphsfiles[$$i]}"
		${PYTHON} ${SCRIPTDIR}/update-overhang-fea.py $${fonts[$$i]} $${glyphsfiles[$$i]}/fontinfo.plist
	done

${FONTDIR}/%.ttf: ${SOURCEDIR}/%.glyphspackage ${SOURCEDIR}/%.glyphspackage/fontinfo.plist
	$(info   BUILD  ${@F})
	export SOURCE_DATE_EPOCH=$(shell stat -c "%Y" $<)
	${PYTHON} -m fontmake $< \
			      --output-path=$@ \
			      --output=variable \
			      --verbose=WARNING \
			      --flatten-components \
			      --filter=... \
			      --filter="alifTools.filters::VariableFeaConvertorFilter(default='MSHQ=10')" \
			      --filter="alifTools.filters::ClearPlaceholdersFilter()" \
			      --filter="alifTools.filters::FontVersionFilter(fontVersion=${VERSION})"

${TESTDIR}/%.json: ${TESTDIR}/%.yaml ${FONTS}
	$(info   GEN    ${@F})
	${PYTHON} -m alifTools.shaping.update $< $@ ${FONTS}

${TESTDIR}/%-shaping.html: ${FONTDIR}/%.ttf ${TESTDIR}/shaping-config.yaml
	$(info   SHAPE  ${<F})
	${PYTHON} -m alifTools.shaping.check $< ${TESTDIR}/shaping-config.yaml $@

${SVG}: ${FONTS}
	$(info   SVG    ${@F})
	${PYTHON} -m alifTools.sample $< \
				      --foreground=1F2328 \
				      --dark-foreground=D1D7E0 \
				      -o $@

dist: ${FONTS}
	$(info   DIST   ${DIST}.zip)
	install -Dm644 -t ${DIST} ${FONTS}
	install -Dm644 -t ${DIST} {README,README-Arabic}.txt
	install -Dm644 -t ${DIST} LICENSE
	zip -rq ${DIST}.zip ${DIST}

clean:
	rm -rf ${FONTS} ${HTML} ${SVG} ${DIST} ${DIST}.zip
