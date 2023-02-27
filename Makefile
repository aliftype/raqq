# Copyright (c) 2020-2021 Khaled Hosny
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

NAME = RaqqText

MAKEFLAGS := -sr
SHELL = bash

CONFIG = _config.yml
VERSION = $(shell python version.py $(CONFIG))
DIST = $(NAME)-$(VERSION)

FEZ = Raqq.fez

ARGS ?= 

.SECONDARY:

.PHONY: all dist

all: $(NAME).otf # $(NAME).ttf

%.fea: %.glyphs $(FEZ)
	$(info   GEN    $(@F))
	python fez-to-fea.py $+ -o $@

%.otf: %.glyphs $(CONFIG) GlyphData.xml %.fea
	$(info   BUILD  $(@F))
	python build.py $< $(VERSION) $@ --data=GlyphData.xml $(ARGS)

%.ttf: %.glyphs $(CONFIG) GlyphData.xml %.fea
	$(info   BUILD  $(@F))
	python build.py $< $(VERSION) $@ --data=GlyphData.xml $(ARGS)

dist: all
	$(info   DIST   $(DIST).zip)
	install -Dm644 -t $(DIST) $(NAME).otf
	#install -Dm644 -t $(DIST) {README,README-Arabic}.txt
	#install -Dm644 -t $(DIST) OFL.txt
	zip -rq $(DIST).zip $(DIST)
