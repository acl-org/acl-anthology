#! /bin/bash
# -*- coding: utf-8 -*-
#
# Copyright 2021 Arne Köhn <arne@chark.eu>
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

set -e
set -u

# modify these two variables to your needs.
# This is the URL under which your mirror will be accessible.
# Note: There is no slash at the end.
export ANTHOLOGY_PREFIX="https://example.com/aclmirror"

# The directory under which the HTML files will reside
export ANTHOLOGY_HTML_ROOT="/var/www/aclmirror"

# this is the directory under which the additional files
# (PDFs, attachments, etc) will be stored.  This directory
# needs to be accessible by the webserver (depending on your
# configuration, it might not need to be under the www
# document root).
export ANTHOLOGYFILES="/anthology-files"

# This is the directory where the anthology git will be cloned
# to and the website will be built.
export GITDIR="/home/anthology/anthology-git-dir"

# initialize if necessary
if [[ ! -e $GITDIR ]]; then
    mkdir -p $GITDIR
fi
cd $GITDIR
if [[ ! -e .git ]]; then
    git clone https://github.com/acl-org/acl-anthology .
fi

ANTHOLOGYDIR=$(echo "${ANTHOLOGY_PREFIX}" | sed 's|https*://[^/]*/\(.*\)|\1|')

if git pull -q; then
    make -j4
    make mirror-no-attachments
    rsync -av --delete build/website/$ANTHOLOGYDIR $ANTHOLOGY_HTML_ROOT
fi
