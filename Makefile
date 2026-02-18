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
# - a command running python should always be invoked with 'uv run python ...';
#   add dependencies via 'uv add' in the root folder.
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

# these are shown in the generated html so everyone knows when the data
# was generated.
timestamp=$(shell date -u +"%d %B %Y at %H:%M %Z")
githash=$(shell git rev-parse HEAD)
githashshort=$(shell git rev-parse --short HEAD)

# uv check
ifeq (, $(shell which uv ))
  $(error "uv not found in $(PATH)")
endif

# hugo version check
HUGO_VERSION_MIN=140
HUGO_VERSION=$(shell hugo version | sed 's/^.* v0\.\(.*\)\..*/\1/')
HUGO_VERSION_TOO_LOW:=$(shell [[ $(HUGO_VERSION_MIN) -gt $(HUGO_VERSION) ]] && echo true)
ifeq ($(HUGO_VERSION_TOO_LOW),true)
  $(error "incorrect hugo version installed! Need hugo 0.$(HUGO_VERSION_MIN), but only found hugo 0.$(HUGO_VERSION)!")
endif


.PHONY: site
site: build/.hugo build/.sitemap


# Split the file sitemap into Google-ingestible chunks.
# Also build the PDF sitemap, and split it.
.PHONY: sitemap
sitemap: build/.sitemap

build/.sitemap: build/.hugo
	uv run python bin/split_sitemap.py build/website/$(ANTHOLOGYDIR)/sitemap.xml
	@rm -f build/website/$(ANTHOLOGYDIR)/sitemap_*.xml.gz
	@gzip -9n build/website/$(ANTHOLOGYDIR)/sitemap_*.xml
	@bin/create_sitemapindex.sh `ls build/website/$(ANTHOLOGYDIR)/ | grep 'sitemap_.*xml.gz'` > build/website/$(ANTHOLOGYDIR)/sitemapindex.xml
	@touch build/.sitemap

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

.PHONY: hugo_data
hugo_data: build/.data

build/.data: build/.basedirs $(sourcefiles)
	@echo "INFO     Generating data files for Hugo..."
	uv run python bin/create_hugo_data.py --clean
	@touch build/.data

.PHONY: bib
bib:	build/.bib

#######################################################
# Disable citation targets (except for 3 bibtex per volume) by setting NOBIB=true
ifeq (true, $(NOBIB))
$(info WARNING: not creating full citation materials; this is not suitable for release!)
build/.bib:
	@touch build/.bib
else

build/.bib: build/.basedirs build/.data
	@echo "INFO     Creating extra bibliographic files..."
	uv run python bin/create_extra_bib.py --clean
	@touch build/.bib
endif
# end if block to conditionally disable bibtex generation
#######################################################

.PHONY: hugo
hugo: build/.hugo

build/.hugo: build/.static build/.data build/.bib
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
mirror:
	uv run python bin/create_mirror.py data/xml/*xml

.PHONY: mirror-no-attachments
mirror-no-attachments:
	uv run python bin/create_mirror.py --only-papers data/xml/*xml

.PHONY: clean
clean:
	rm -rf build .venv

.PHONY: check
check:
	@if grep -rl '	' data/xml; then \
	    echo "check error: found a tab character in the above XML files!"; \
	    exit 1; \
	fi
	SKIP=no-commit-to-branch uv run pre-commit run --all-files

.PHONY: check_commit
check_commit:
	uv run pre-commit run

.PHONY: autofix
autofix: check

.PHONY: reformat
reformat: autofix

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
