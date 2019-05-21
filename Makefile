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
site: static yaml hugo_pages bibtex mods endnote hugo

.PHONY: all
all: clean check site

# copies all files that are not automatically generated
# and creates empty directories as needed.
.PHONY: static
static:
	@echo "INFO     Creating and populating build directory..."
	@mkdir -p build
	@cp -r hugo/* build
	@mkdir -p build/data-export
	@perl -pi -e "s/ANTHOLOGYDIR/$(ANTHOLOGYDIR)/g" build/index.html

.PHONY: yaml
yaml:
	@echo "INFO     Generating YAML files for Hugo..."
	@python3 bin/create_hugo_yaml.py --clean

.PHONY: hugo_pages
hugo_pages:
	@echo "INFO     Creating page templates for Hugo..."
	@python3 bin/create_hugo_pages.py --clean

.PHONY: bibtex
bibtex:
	@echo "INFO     Creating BibTeX files..."
	python3 bin/create_bibtex.py --clean

.PHONY: mods
mods:
	@echo "INFO     Converting BibTeX files to MODS XML..."
	@if ! [ -x "`command -v tqdm`" ]; then \
	  find build/data-export -name '*.bib' -print0 | \
	      xargs -0 -n 1 -P 8 bin/bib2xml_wrapper >/dev/null; \
	else \
	  find build/data-export -name '*.bib' -print0 | \
	      xargs -0 -n 1 -P 8 bin/bib2xml_wrapper | \
	      tqdm --total `find build/data-export -name '*.bib' | wc -l` \
               --unit files >/dev/null; \
	fi

.PHONY: endnote
endnote:
	@echo "INFO     Converting MODS XML files to EndNote..."
	@if ! [ -x "`command -v tqdm`" ]; then \
	  find build/data-export -name '*.xml' -print0 | \
	      xargs -0 -n 1 -P 8 bin/xml2end_wrapper >/dev/null; \
	else \
	  find build/data-export -name '*.xml' -print0 | \
	      xargs -0 -n 1 -P 8 bin/xml2end_wrapper | \
	      tqdm --total `find build/data-export -name '*.xml' | wc -l` \
	           --unit files >/dev/null; \
	fi

.PHONY: hugo
hugo:
	@echo "INFO     Running Hugo... this may take a while."
	@cd build && \
	    hugo -b $(ANTHOLOGYHOST)/$(ANTHOLOGYDIR) \
	         -d $(ANTHOLOGYDIR) \
	         --cleanDestinationDir \
	         --minify

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
