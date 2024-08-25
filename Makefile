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
MAKEFLAGS := -srj
PYTHON := venv/bin/python3

CONFIG = docs/_config.yml
VERSION = $(shell grep "version:" $(CONFIG) | sed -e 's/.*.: "\(.*.\)".*/\1/')
DIST = $(NAME)-$(VERSION)

SOURCEDIR = sources
SCRIPTDIR = scripts
FONTDIR = fonts
TESTDIR = tests
BUILDDIR = build
WOFFDIR = docs/assets/fonts

NAMES = $(NAME) $(NAME)Sura
FONTS = $(NAMES:%=$(FONTDIR)/%.ttf)
WOFF2 = $(NAMES:%=$(WOFFDIR)/%.woff2)

TESTS = shaping decomposition
JSON = $(TESTS:%=$(TESTDIR)/%.json)

FEA = $(NAMES:%=$(SOURCEDIR)/%-overhang.fea)
HTML = $(NAMES:%=$(TESTDIR)/%-shaping.html) $(NAMES:%=$(TESTDIR)/%-qa.html)
GLYPHDATA = $(SOURCEDIR)/GlyphData.xml

ARGS ?= 

.SECONDARY:
.ONESHELL:
.PHONY: all dist ttf web

all: ttf web
ttf: $(FONTS)
test: $(HTML)
expectation: $(JSON)

web: $(WOFF2)

update-fea: $(FONTS)
	fonts=($(FONTS))
	fea=($(FEA))
	for i in $${!fonts[@]}; do
		echo "  GEN    $${fea[$$i]}"
		${PYTHON} $(SCRIPTDIR)/update-overhang-fea.py $${fonts[$$i]} $${fea[$$i]}
	done

$(FONTDIR)/%.ttf: $(SOURCEDIR)/%.glyphspackage $(CONFIG) $(GLYPHDATA) $(SOURCEDIR)/%-overhang.fea
	$(info   BUILD  $(@F))
	${PYTHON} $(SCRIPTDIR)/build.py $< $(VERSION) $@ --data=$(GLYPHDATA) $(ARGS)

$(WOFFDIR)/%.woff2: $(FONTDIR)/%.ttf
	$(info   WOFF2  $(@F))
	${PYTHON} $(SCRIPTDIR)/buildwoff2.py $< $@

$(TESTDIR)/%-shaping.html: $(FONTDIR)/%.ttf $(TESTDIR)/fontbakery.yml
	$(info   SHAPE  $(<F))
	${PYTHON} -m fontbakery check-shaping --config=$(TESTDIR)/fontbakery.yml $< --html=$@ -e WARN -q

$(TESTDIR)/%-qa.html: $(FONTDIR)/%.ttf $(TESTDIR)/fontbakery.yml
	$(info   TEST   $(<F))
	${PYTHON} -m fontbakery check-universal --config=$(TESTDIR)/fontbakery.yml $< --html=$@ -e WARN -q

$(TESTDIR)/decomposition.json: $(SOURCEDIR)/$(NAME).glyphspackage $(FONTS)
	$(info   GEN    $(@F))
	${PYTHON} $(SCRIPTDIR)/update-decomposition-test.py $@ $+

$(TESTDIR)/shaping.json: $(TESTDIR)/shaping.csv $(FONTS)
	$(info   GEN    $(@F))
	${PYTHON} $(SCRIPTDIR)/update-shaping-test.py $@ $+

dist: all
	$(info   DIST   $(DIST).zip)
	install -Dm644 -t $(DIST) $(FONTS)
	install -Dm644 -t $(DIST) {README,README-Arabic}.txt
	install -Dm644 -t $(DIST) LICENSE
	zip -rq $(DIST).zip $(DIST)
