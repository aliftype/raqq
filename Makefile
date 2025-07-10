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

NAME = Raqq

SHELL = bash
MAKEFLAGS := -sr
PYTHON := venv/bin/python3

SOURCEDIR = sources
SCRIPTDIR = scripts
FONTDIR = fonts
TESTDIR = tests
BUILDDIR = build

NAMES = ${NAME} ${NAME}Sura
FONTS = ${NAMES:%=${FONTDIR}/%.ttf}

JSON = ${TESTDIR}/shaping.json

FEA = ${NAMES:%=${SOURCEDIR}/%-overhang.fea}
HTML = ${NAMES:%=${TESTDIR}/%-shaping.html}

TAG = $(shell git describe --tags --abbrev=0)
VERSION = ${TAG:v%=%}
DIST = ${NAME}-${VERSION}


.SECONDARY:
.ONESHELL:
.PHONY: all clean dist ttf test

all: ttf
ttf: ${FONTS}
test: ${HTML}
expectation: ${JSON}

update-fea: ${FONTS}
	fonts=(${FONTS})
	fea=(${FEA})
	for i in $${!fonts[@]}; do
		echo "  GEN    $${fea[$$i]}"
		${PYTHON} ${SCRIPTDIR}/update-overhang-fea.py $${fonts[$$i]} $${fea[$$i]}
	done

${FONTDIR}/%.ttf: ${SOURCEDIR}/%.glyphspackage ${SOURCEDIR}/%-overhang.fea
	$(info   BUILD  ${@F})
	${PYTHON} ${SCRIPTDIR}/build.py $< ${VERSION} $@

${TESTDIR}/shaping.json: ${TESTDIR}/shaping.yaml ${FONTS}
	$(info   GEN    ${@F})
	${PYTHON} -m alifTools.shaping.update $< $@ ${FONTS}

${TESTDIR}/%-shaping.html: ${FONTDIR}/%.ttf ${TESTDIR}/shaping-config.yml
	$(info   SHAPE  ${<F})
	${PYTHON} -m alifTools.shaping.check $< ${TESTDIR}/shaping-config.yml $@

dist: ${FONTS}
	$(info   DIST   ${DIST}.zip)
	install -Dm644 -t ${DIST} ${FONTS}
	install -Dm644 -t ${DIST} {README,README-Arabic}.txt
	install -Dm644 -t ${DIST} LICENSE
	zip -rq ${DIST}.zip ${DIST}

clean:
	rm -rf ${FONTS} ${HTML} ${DIST} ${DIST}.zip
