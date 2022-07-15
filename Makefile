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

NAME = Raqq

MAKEFLAGS := -sr
SHELL = bash

CONFIG = _config.yml
VERSION = $(shell python version.py $(CONFIG))
DIST = $(NAME)-$(VERSION)

FEZ = $(wildcard *.fez)

ARGS ?= 

.PHONY: all dist

all: $(NAME).otf # $(NAME).ttf

%.otf: $(NAME).glyphs $(CONFIG) GlyphData.xml $(FEZ)
	$(info   BUILD  $(@F))
	python build.py $< $(VERSION) $@ --data=GlyphData.xml $(ARGS)

%.ttf: $(NAME).glyphs $(CONFIG) GlyphData.xml $(FEZ)
	$(info   BUILD  $(@F))
	python build.py $< $(VERSION) $@ --data=GlyphData.xml $(ARGS)

dist: all
	$(info   DIST   $(DIST).zip)
	install -Dm644 -t $(DIST) $(NAME)-Regular.otf
	#install -Dm644 -t $(DIST) {README,README-Arabic}.txt
	#install -Dm644 -t $(DIST) OFL.txt
	zip -rq $(DIST).zip $(DIST)
