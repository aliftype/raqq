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

NAME = Raqq

MAKEFLAGS := -sr
SHELL = bash

CONFIG = _config.yml
VERSION = $(shell grep "version:" $(CONFIG) | sed -e 's/.*.: "\(.*.\)".*/\1/')
DIST = $(NAME)-$(VERSION)

SOURCEDIR = sources
SCRIPTDIR = scripts
FONTDIR = fonts
TESTDIR = tests
BUILDDIR = build

FONTS = $(FONTDIR)/$(NAME).ttf
WOFF2 = $(FONTDIR)/$(NAME).woff2
FEA = $(SOURCEDIR)/overhang.fea
JSON = $(TESTDIR)/shaping.json $(TESTDIR)/decomposition.json
HTML = $(TESTDIR)/$(NAME).html
GLYPHDATA = $(SOURCEDIR)/GlyphData.xml

ARGS ?= 

.SECONDARY:
.ONESHELL:
.PHONY: all dist

ttf: $(FONTS)
web: $(WOFF2)
all: ttf web
test: $(HTML)
update-test: $(JSON)

update-fea: $(FONTS)
	$(info   GEN    $(@F))
	python $(SCRIPTDIR)/update-overhang-fea.py $< $(FEA)

$(FONTDIR)/%.ttf: $(SOURCEDIR)/%.glyphs $(CONFIG) $(GLYPHDATA) $(FEA)
	$(info   BUILD  $(@F))
	python $(SCRIPTDIR)/build.py $< $(VERSION) $@ --data=$(GLYPHDATA) $(ARGS)

$(FONTDIR)/%.woff2: $(FONTDIR)/%.ttf
	$(info   WOFF2  $(@F))
	python $(SCRIPTDIR)/buildwoff2.py $< $@

$(TESTDIR)/%.html: $(FONTDIR)/%.ttf $(TESTDIR)/fontbakery.yml
	$(info   TEST   $(<F))
	fontbakery check-universal --config=$(TESTDIR)/fontbakery.yml \
                   fontbakery.profiles.shaping $< --html=$@ -l WARN &> /dev/null

$(TESTDIR)/decomposition.json: $(SOURCEDIR)/$(NAME).glyphs $(FONTS)
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
