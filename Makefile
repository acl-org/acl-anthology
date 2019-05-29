# -*- coding: utf-8 -*-
#
# Copyright 2019 Arne Köhn <arne@chark.eu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

SHELL = /bin/sh
ANTHOLOGYHOST := "https://aclweb.org"
ANTHOLOGYDIR := anthology

.PHONY: site
site: bibtex mods endnote hugo

.PHONY: all
all: clean check site

# copies all files that are not automatically generated
# and creates empty directories as needed.
.PHONY: static
static: build/.static

build/.static:
	@echo "INFO     Creating and populating build directory..."
	@mkdir -p build
	@cp -r hugo/* build
	@mkdir -p build/data-export
	@perl -pi -e "s/ANTHOLOGYDIR/$(ANTHOLOGYDIR)/g" build/index.html
	@touch build/.static

.PHONY: yaml
yaml: build/.yaml

build/.yaml: build/.static
	@echo "INFO     Generating YAML files for Hugo..."
	@python3 bin/create_hugo_yaml.py --clean
	@touch build/.yaml

.PHONY: hugo_pages
hugo_pages: build/.pages

build/.pages: build/.static build/.yaml
	@echo "INFO     Creating page templates for Hugo..."
	@python3 bin/create_hugo_pages.py --clean
	@touch build/.pages

.PHONY: bibtex
bibtex:	build/.bibtex

build/.bibtex: build/.static
	@echo "INFO     Creating BibTeX files..."
	python3 bin/create_bibtex.py --clean
	@touch build/.bibtex

.PHONY: mods
mods: build/.mods

build/.mods: build/.static
	@echo "INFO     Converting BibTeX files to MODS XML..."
	find build/data-export -name '*.bib' -print0 | \
	      xargs -0 -n 1 -P 8 bin/bib2xml_wrapper >/dev/null
	@touch build/.mods

.PHONY: endnote
endnote: build/.endnote

build/.endnote: build/.mods
	@echo "INFO     Converting MODS XML files to EndNote..."
	find build/data-export -name '*.xml' -print0 | \
	      xargs -0 -n 1 -P 8 bin/xml2end_wrapper >/dev/null
	@touch build/.endnote

%.endf: %.xml
	xml2end $< 2>&1 > $@

.PHONY: hugo
hugo: build/.hugo

build/.hugo: build/.pages build/.bibtex build/.mods build/.endnote
	@echo "INFO     Running Hugo... this may take a while."
	@cd build && \
	    hugo -b $(ANTHOLOGYHOST)/$(ANTHOLOGYDIR) \
	         -d $(ANTHOLOGYDIR) \
	         --cleanDestinationDir \
	         --minify
	@touch build/.hugo

.PHONY: clean
clean:
	rm -rf build

.PHONY: check
check:
	jing -c data/xml/schema.rnc data/xml/*xml

.PHONY: serve
serve:
	 @echo "INFO     Starting a server at http://localhost:8000/"
	 @cd build && python3 -m http.server 8000

# this target does not use ANTHOLOGYDIR because the official website
# only works if ANTHOLOGYDIR == anthology.
.PHONY: upload
upload:
	@if [[ $(ANTHOLOGYDIR) != "anthology" ]]; then \
            echo "WARNING: Can't upload because ANTHOLOGYDIR was set to '$(ANTHOLOGYDIR)' instead of 'anthology'"; \
            exit 1; \
        fi
	@echo "INFO     Running rsync..."
	@rsync -azve ssh --delete build/anthology/ aclweb:anthology-static
