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

MAKEFLAGS := -sr
SHELL = bash

CONFIG = docs/_config.yml
VERSION = $(shell grep "version:" $(CONFIG) | sed -e 's/.*.: "\(.*.\)".*/\1/')
DIST = $(NAME)-$(VERSION)

SOURCEDIR = sources
SCRIPTDIR = scripts
FONTDIR = fonts
TESTDIR = tests
BUILDDIR = build

NAMES = $(NAME) $(NAME)Sura
FONTS = $(NAMES:%=$(FONTDIR)/%.ttf)
WOFF2 = $(FONTS:%.ttf=%.woff2)

TESTS = shaping decomposition
JSON = $(TESTS:%=$(TESTDIR)/%.json)


FEA = $(SOURCEDIR)/overhang.fea
HTML = $(NAMES:%=$(TESTDIR)/%-shaping.html) $(NAMES:%=$(TESTDIR)/%-fb.html)
GLYPHDATA = $(SOURCEDIR)/GlyphData.xml

ARGS ?= 

.SECONDARY:
.ONESHELL:
.PHONY: all dist

all: ttf web
ttf: $(FONTS)
test: $(HTML)
update-test: $(JSON)

web: $(WOFF2)
	cp $+ docs/assets/fonts/

update-fea: $(FONTS)
	$(info   GEN    $(@F))
	python $(SCRIPTDIR)/update-overhang-fea.py $< $(FEA)

$(FONTDIR)/%Sura.ttf: $(SOURCEDIR)/%Sura.glyphspackage $(CONFIG) $(GLYPHDATA) $(FEA)
	$(info   BUILD  $(@F))
	python $(SCRIPTDIR)/build.py $< $(VERSION) $@ --data=$(GLYPHDATA) --no-SVG $(ARGS)

$(FONTDIR)/%.ttf: $(SOURCEDIR)/%.glyphspackage $(CONFIG) $(GLYPHDATA) $(FEA)
	$(info   BUILD  $(@F))
	python $(SCRIPTDIR)/build.py $< $(VERSION) $@ --data=$(GLYPHDATA) $(ARGS)

$(FONTDIR)/%.woff2: $(FONTDIR)/%.ttf
	$(info   WOFF2  $(@F))
	python $(SCRIPTDIR)/buildwoff2.py $< $@

$(TESTDIR)/%-shaping.html: $(FONTDIR)/%.ttf $(TESTDIR)/fontbakery.yml
	$(info   SHAPE  $(<F))
	fontbakery check-shaping --config=$(TESTDIR)/fontbakery.yml $< --html=$@ -l WARN -e WARN &> /dev/null

$(TESTDIR)/%-fb.html: $(FONTDIR)/%.ttf $(TESTDIR)/fontbakery.yml
	$(info   TEST   $(<F))
	fontbakery check-universal --config=$(TESTDIR)/fontbakery.yml $< --html=$@ -l WARN -e WARN &> /dev/null

$(TESTDIR)/decomposition.json: $(SOURCEDIR)/$(NAME).glyphspackage $(FONTS)
	$(info   GEN    $(@F))
	python $(SCRIPTDIR)/update-decomposition-test.py $@ $+

$(TESTDIR)/shaping.json: $(TESTDIR)/shaping.csv $(FONTS)
	$(info   GEN    $(@F))
	python $(SCRIPTDIR)/update-shaping-test.py $@ $+

dist: all
	$(info   DIST   $(DIST).zip)
	install -Dm644 -t $(DIST) $(FONTS)
	install -Dm644 -t $(DIST) {README,README-Arabic}.txt
	install -Dm644 -t $(DIST) LICENSE
	zip -rq $(DIST).zip $(DIST)
