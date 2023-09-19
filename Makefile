# -*- coding: utf-8 -*-
#
# Copyright 2019-2021 Arne Köhn <arne@chark.eu>
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

# Instructions:
# - if you edit a command running python, make sure to
#   write . $(VENV) && python3 -- this sets up the virtual environment.
#   if you just write "python3 foo.py" without the ". $(VENV) && " before,
#   the libraries will not be loaded during run time.
# - all targets running python somewhere should have venv/bin/activate as a dependency.
#   this makes sure that all required packages are installed.
# - Disable bibtex etc. targets by setting NOBIB=true (for debugging etc.)
#   (e.g., make -j4 NOBIB=true)

SHELL := /bin/bash

# If you want to host the anthology on your own, set ANTHOLOGY_PREFIX
# in your call to make to your prefix, e.g.
#
#     ANTHOLOGY_PREFIX="https://mirror.myhost.com/anthology" make
#
# PLEASE NOTE that the prefix cannot contain any '#' character, or a Perl regex
# below will fail.
# The following line ensures that it is exported as an environment variable
# for all sub-processes:

export ANTHOLOGY_PREFIX ?= https://aclanthology.org

SLASHATEND:=$(shell echo ${ANTHOLOGY_PREFIX} | grep -q '/$$'; echo $$?)

ifeq (${SLASHATEND},0)
  $(error ANTHOLOGY_PREFIX is not allowed to have a slash at the end.)
endif

# hugo wants to know the host and base dir on its own, so
# we sed the prefix into those parts.
ANTHOLOGYHOST := $(shell echo "${ANTHOLOGY_PREFIX}" | sed 's|\(https*://[^/]*\).*|\1|')
ANTHOLOGYDIR := $(shell echo "${ANTHOLOGY_PREFIX}" | sed 's|https*://[^/]*/\(.*\)|\1|')

# the regexp above only matches if we actually have a subdirectory.
# make the dir empty if only a tld was provided as the prefix.
ifeq ($(ANTHOLOGY_PREFIX),$(ANTHOLOGYDIR))
  ANTHOLOGYDIR :=
endif

# Root location for PDF and attachment hierarchy.
# This is the directory where you have to put all the papers and attachments.
# Easiest if the server can just serve them from /anthology-files.
ANTHOLOGYFILES ?= /var/www/anthology-files

HUGO_ENV ?= production

sourcefiles=$(shell find data -type f '(' -name "*.yaml" -o -name "*.xml" ')')
xmlstaged=$(shell git diff --staged --name-only --diff-filter=d data/xml/*.xml)
pysources=$(shell git ls-files | egrep "\.pyi?$$")
pystaged=$(shell git diff --staged --name-only  --diff-filter=d | egrep "\.pyi?$$")

# these are shown in the generated html so everyone knows when the data
# was generated.
timestamp=$(shell date -u +"%d %B %Y at %H:%M %Z")
githash=$(shell git rev-parse HEAD)
githashshort=$(shell git rev-parse --short HEAD)

#######################################################
# check whether the correct python version is available
ifeq (, $(shell which python3 ))
  $(error "python3 not found in $(PATH)")
endif

PYTHON_VERSION_MIN=3.8
PYTHON_VERSION_OK=$(shell python3 -c 'import sys; (major, minor) = "$(PYTHON_VERSION_MIN)".split("."); print(sys.version_info.major==int(major) and sys.version_info.minor >= int(minor))' )

ifeq ($(PYTHON_VERSION_OK),"False")
  PYTHON_VERSION=$(shell python3 -c 'import sys; print("%d.%d"% sys.version_info[0:2])' )
  $(error "Need python $(PYTHON_VERSION_MIN), but only found python $(PYTHON_VERSION)!")
endif
# end python check
#######################################################

# hugo version check
HUGO_VERSION_MIN=114
HUGO_VERSION=$(shell hugo version | sed 's/^.* v0\.\(.*\)\..*/\1/')
HUGO_VERSION_TOO_LOW:=$(shell [[ $(HUGO_VERSION_MIN) -gt $(HUGO_VERSION) ]] && echo true)
ifeq ($(HUGO_VERSION_TOO_LOW),true)
  $(error "incorrect hugo version installed! Need hugo 0.$(HUGO_VERSION_MIN), but only found hugo 0.$(HUGO_VERSION)!")
endif

# check whether bibtools are installed; used by the endnote and mods targets.
HAS_XML2END=$(shell which xml2end > /dev/null && echo true || echo false)
HAS_BIB2XML=$(shell which bib2xml > /dev/null && echo true || echo false)


VENV := "venv/bin/activate"

.PHONY: site
site: build/.hugo build/.sitemap


# Split the file sitemap into Google-ingestible chunks.
# Also build the PDF sitemap, and split it.
.PHONY: sitemap
sitemap: build/.sitemap

build/.sitemap: venv/bin/activate build/.hugo
	. $(VENV) && python3 bin/split_sitemap.py build/website/$(ANTHOLOGYDIR)/sitemap.xml
	@rm -f build/website/$(ANTHOLOGYDIR)/sitemap_*.xml.gz
	@gzip -9n build/website/$(ANTHOLOGYDIR)/sitemap_*.xml
	@bin/create_sitemapindex.sh `ls build/website/$(ANTHOLOGYDIR)/ | grep 'sitemap_.*xml.gz'` > build/website/$(ANTHOLOGYDIR)/sitemapindex.xml
	@touch build/.sitemap

.PHONY: venv
venv: venv/bin/activate

# installs dependencies if requirements.txt have been updated.
# checks whether libyaml is enabled to ensure fast build times.
venv/bin/activate: bin/requirements.txt
	test -d venv || python3 -m venv venv
	. $(VENV) && pip3 install wheel
	. $(VENV) && pip3 install -Ur bin/requirements.txt
	@. $(VENV) && python3 -c "from yaml import CLoader" 2> /dev/null || ( \
	    echo "WARNING     No libyaml bindings enabled for pyyaml, your build will be several times slower than needed";\
	    echo "            see the README on GitHub for more information")
	touch venv/bin/activate

.PHONY: all
all: check site

.PHONY: basedirs
basedirs:
	build/.basedirs

build/.basedirs:
	@mkdir -p build/data-export
	@mkdir -p build/content/papers
	@touch build/.basedirs

# copies all files that are not automatically generated
# and creates empty directories as needed.
.PHONY: static
static: build/.static

build/.static: build/.basedirs $(shell find hugo -type f)
	@echo "INFO     Creating and populating build directory..."
	@echo "INFO     Split ${ANTHOLOGY_PREFIX} into HOST=${ANTHOLOGYHOST} DIR=${ANTHOLOGYDIR}"
	@cp -r hugo/* build
	@echo >> build/config.toml
	@echo "[params]" >> build/config.toml
	@echo "  githash = \"${githash}\"" >> build/config.toml
	@echo "  githashshort = \"${githashshort}\"" >> build/config.toml
	@echo "  timestamp = \"${timestamp}\"" >> build/config.toml
	@perl -pi -e "s|ANTHOLOGYDIR|$(ANTHOLOGYDIR)|g" build/website/index.html
	@touch build/.static

.PHONY: yaml
yaml: build/.yaml

build/.yaml: build/.basedirs $(sourcefiles) venv/bin/activate
	@echo "INFO     Generating YAML files for Hugo..."
	. $(VENV) && python3 bin/create_hugo_yaml.py --clean
	@touch build/.yaml

.PHONY: hugo_pages
hugo_pages: build/.pages

build/.pages: build/.basedirs build/.yaml venv/bin/activate
	@echo "INFO     Creating page templates for Hugo..."
	. $(VENV) && python3 bin/create_hugo_pages.py --clean
	@touch build/.pages

.PHONY: bibtex
bibtex:	build/.bibtex

.PHONY: mods
mods: build/.mods

.PHONY: endnote
endnote: build/.endnote

#######################################################
build/.bibtex: build/.basedirs $(sourcefiles) venv/bin/activate
	@echo "INFO     Creating BibTeX files..."
	. $(VENV) && python3 bin/create_bibtex.py --clean
	@touch build/.bibtex

# Disable citation targets (except for 3 bibtex per volume) by setting NOBIB=true
ifeq (true, $(NOBIB))
$(info WARNING: not creating citation materials; this is not suitable for release!)
build/.mods: build/.bibtex
	touch build/.mods
build/.endnote: build/.bibtex
	touch build/.endnote
else

build/.mods: build/.bibtex
	@if [ $(HAS_BIB2XML) = false ]; then \
	    echo "bib2xml not found, please install bibtools"; \
            echo "alternatively, build the site without endnote files by running make hugo"; \
	    exit 1; \
	fi
	@echo "INFO     Converting BibTeX files to MODS XML..."
	@find build/data-export -name '*.bib' -print0 | \
	      xargs -0 -n 1 -P 8 bin/bib2xml_wrapper >/dev/null
	@touch build/.mods

build/.endnote: build/.mods
	@if [ $(HAS_XML2END) = false ]; then \
	    echo "xml2end not found, please install bibtools"; \
            echo "alternatively, build the site without endnote files by running make hugo"; \
	    exit 1; \
	fi
	@echo "INFO     Converting MODS XML files to EndNote..."
	@find build/data-export -name '*.xml' -print0 | \
	      xargs -0 -n 1 -P 8 bin/xml2end_wrapper >/dev/null
	@touch build/.endnote
endif
# end if block to conditionally disable bibtex generation
#######################################################


%.endf: %.xml
	xml2end $< 2>&1 > $@

.PHONY: hugo
hugo: build/.hugo

build/.hugo: build/.static build/.pages build/.bibtex build/.mods build/.endnote
	@echo "INFO     Running Hugo... this may take a while."
	@cd build && \
	    hugo -b $(ANTHOLOGYHOST)/$(ANTHOLOGYDIR) \
	         -d website/$(ANTHOLOGYDIR) \
		 -e $(HUGO_ENV) \
	         --cleanDestinationDir \
	         --minify \
		 --logLevel=info
	@cd build/website/$(ANTHOLOGYDIR) \
	    && ln -s $(ANTHOLOGYFILES) anthology-files \
	    && perl -i -pe 's|ANTHOLOGYDIR|$(ANTHOLOGYDIR)|g' .htaccess
	@touch build/.hugo

.PHONY: mirror
mirror: venv/bin/activate
	. $(VENV) && bin/create_mirror.py data/xml/*xml

.PHONY: mirror-no-attachments
mirror-no-attachments: venv/bin/activate
	. $(VENV) && bin/create_mirror.py --only-papers data/xml/*xml

.PHONY: test
test: hugo
	diff -u build/website/$(ANTHOLOGYDIR)/P19-1007.bib test/data/P19-1007.bib
	diff -u build/website/$(ANTHOLOGYDIR)/P19-1007.xml test/data/P19-1007.xml

.PHONY: clean
clean:
	rm -rf build venv

.PHONY: check
check: venv pytest
	@if grep -rl '	' data/xml; then \
	    echo "check error: found a tab character in the above XML files!"; \
	    exit 1; \
	fi
	jing -c data/xml/schema.rnc data/xml/*xml
	. $(VENV) \
	  && SKIP=no-commit-to-branch pre-commit run --all-files \
	  && black --check $(pysources) \
	  && ruff check $(pysources)

.PHONY: pytest
pytest: venv
	. $(VENV) && PYTHONPATH=bin/ python -m pytest tests --cov-report term --cov=anthology tests

.PHONY: check_staged_xml
check_staged_xml:
	@if [ ! -z "$(xmlstaged)" ]; then \
	     jing -c data/xml/schema.rnc $(xmlstaged) ;\
	 fi

.PHONY: check_commit
check_commit: check_staged_xml venv/bin/activate
	@. $(VENV) && pre-commit run
	@if [ ! -z "$(pystaged)" ]; then \
	    . $(VENV) && black --check $(pystaged) && ruff check $(pystaged) ;\
	 fi

.PHONY: autofix
autofix: check_staged_xml venv/bin/activate
	 @. $(VENV) && \
	 EXIT_STATUS=0 ;\
	 pre-commit run || EXIT_STATUS=$$? ;\
	 PRE_DIFF=`git diff --no-ext-diff --no-color` ;\
	 ruff --fix --show-fixes $(pysources) || EXIT_STATUS=$$? ;\
	 black $(pysources) || EXIT_STATUS=$$? ;\
	 POST_DIFF=`git diff --no-ext-diff --no-color` ;\
	 [ "$${PRE_DIFF}" = "$${POST_DIFF}" ] || EXIT_STATUS=1 ;\
	 [ $${EXIT_STATUS} -eq 0 ]

.PHONY: serve
serve:
	 @echo "INFO     Starting a server at http://localhost:8000/"
	 @cd build/website && python3 -m http.server 8000

# Main site: aclanthology.org. Requires ANTHOLOGYDIR to be unset.
.PHONY: upload
upload:
	@if [[ "$(ANTHOLOGYDIR)" != "" ]]; then \
            echo "WARNING: Can't upload because ANTHOLOGYDIR was set to '${ANTHOLOGYDIR}' instead of being empty"; \
            exit 1; \
        fi
	@echo "INFO     Running rsync for main site (aclanthology.org)..."
	@rsync -aze "ssh -o StrictHostKeyChecking=accept-new" --delete build/website/ anthologizer@aclanthology.org:/var/www/aclanthology.org

# Push a preview to the mirror
.PHONY: preview
preview:
	make --version
	@if [[ "$(ANTHOLOGYDIR)" != "" ]]; then \
	  echo "INFO     Running rsync for the '$(ANTHOLOGYDIR)' branch preview..."; \
	  rsync -aze "ssh -o StrictHostKeyChecking=accept-new" build/website/${ANTHOLOGYDIR}/ anthologizer@aclanthology.org:/var/www/preview.aclanthology.org/${ANTHOLOGYDIR}; \
	else \
	  echo "FATAL    ANTHOLOGYDIR must contain the preview name, but was empty"; \
	  exit 1; \
	fi
