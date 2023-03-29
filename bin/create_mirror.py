#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 Arne Köhn <arne@chark.eu>
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

"""Usage: create_mirror.py [--source=SRC] [--to=DIR] [--debug] [--dry-run] [--only-papers] XMLFILE...

Creates YAML files containing all necessary Anthology data for the static website generator.
XMLFILE: data file from the anthology data dir to fetch data for. Use data/xml/*.xml to
fetch everything.

Options:
  --source=SRC               where to fetch the files from [default: https://aclanthology.org]
  --to=DIR                 Directory to write files to [default: {scriptdir}/../build/anthology-files]
  --only-papers            Do not mirror attachments, only papers.
  --debug                  Output debug-level log messages.
  -n, --dry-run            Do not actually download, use with --debug to see what would happen
  -h, --help               Display this helpful text.
"""

import anthology.utils as anthology_utils
from anthology.utils import SeverityTracker
from docopt import docopt
import logging as log
import os
import re
import shutil
import sys
import tempfile

from urllib.request import urlretrieve

from lxml import etree

####  COPY OF .htaccess RULES USED AS GUIDE FOR THE REGULAR EXPRESSIONS BELOW
#############################################################################
# # PDF link, revisions, and errata (P17-1069[v2].pdf loads P/P17/P17-1069[v2].pdf --- with "v2" optional)
# # TODO: decide on a new format for revisions and errata
# RewriteRule ^([A-Za-z])(\d{2})\-(\d{4})([ve]\d+)?\.pdf$ /ANTHOLOGYFILES/pdf/$1/$1$2/$1$2-$3$4.pdf [L,NC]
# RewriteRule ^(\d{4})\.([a-zA-Z\d]+)\-([a-zA-Z\d]+)\.(\d+([ve]\d+)?)\.pdf$ /ANTHOLOGYFILES/pdf/$2/$1.$2-$3.$4.pdf [L,NC]

# # Attachments (e.g., P17-1069.Poster.pdf loads /ANTHOLOGYFILES/attachments/P/P17/P17-1069.Poster.pdf)
# RewriteRule ^attachments/([A-Za-z])(\d{2})\-(\d{4})(\..*)?$ /ANTHOLOGYFILES/attachments/$1/$1$2/$1$2-$3$4 [L,NC]
# RewriteRule ^attachments/(\d{4})\.([a-zA-Z\d]+)\-([a-zA-Z\d]+\.\d+)\.(.*)$ /ANTHOLOGYFILES/attachments/$2/$1.$2-$3.$4 [L,NC]

NEW_ID_RE = re.compile(r"^(\d{4})\.([a-zA-Z\d]+)\-")
OLD_ID_RE = re.compile(r"^([A-Za-z])(\d{2})\-")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class ACLMirrorer:
    def __init__(self, args) -> None:
        self.hash_mismatches = []
        self.not_downloadable = []
        self.args = args
        self.source = args["--source"]
        self.to = args["--to"]
        self.is_dry_run = args["--dry-run"]
        self.only_papers = args["--only-papers"]

    def download_file(self, fname: str, hash: str, type: str) -> None:
        if type == "pdf":
            remote_url = self.source + "/" + fname
        elif type == "attachment":
            remote_url = self.source + "/attachments/" + fname
        else:
            log.error("unrecognized type: " + type)
            exit(1)
        local_target = ""
        # mkstemp opens the file but we only need the file name, so close it again.
        tmpfd, tmp_target = tempfile.mkstemp(prefix="aclmirrorer_", suffix=".pdf")
        os.close(tmpfd)
        match = NEW_ID_RE.match(fname)
        if match:
            local_target = os.path.join(self.to, type, match.groups()[1], fname)
        else:
            match = OLD_ID_RE.match(fname)
            if match:
                local_target = os.path.join(
                    self.to,
                    type,
                    match.groups()[0],
                    match.groups()[0] + match.groups()[1],
                    fname,
                )
            else:
                log.error("unrecognized format for " + fname)
                exit(1)

        if os.path.exists(local_target):
            existing_hash = anthology_utils.compute_hash_from_file(local_target)
            if existing_hash == hash:
                log.debug(
                    "File {} already up to date, not downloading again".format(
                        local_target
                    )
                )
                return
            else:
                log.debug("File {} changed, redownloading ...".format(local_target))
        else:
            log.debug("Downloading {} from {} ...".format(local_target, remote_url))

        if self.is_dry_run:
            return

        local_path = os.path.dirname(local_target)
        os.makedirs(local_path, exist_ok=True)
        try:
            urlretrieve(remote_url, tmp_target)
        except Exception:
            log.error("could not download " + remote_url)
            self.not_downloadable.append(remote_url)
            os.remove(tmp_target)
            return
        new_hash = anthology_utils.compute_hash_from_file(tmp_target)
        if new_hash == hash:
            # all good, store downloaded file in the proper place
            shutil.move(tmp_target, local_target)
        else:
            log.error(
                "Hash mismatch for file {}, downloaded from {}. was {} should be {}".format(
                    local_target, remote_url, new_hash, hash
                )
            )
            self.hash_mismatches.append(remote_url)
        return

    def download_files(self, xmlfname: str):
        xml = etree.parse(xmlfname)
        proceedings = xml.findall("//volume/meta/url[@hash]")
        frontmatter = xml.findall("//frontmatter/url[@hash]")
        papers = xml.findall("//paper/url[@hash]")
        attachments = xml.findall("//paper/attachment[@hash]")
        revisions = xml.findall("//paper/revision[@hash]")
        errata = xml.findall("//paper/erratum[@hash]")
        log.info("processing {} papers from {} ...".format(len(papers), xmlfname))
        for collection in [proceedings, frontmatter, papers, revisions, errata]:
            for entry in collection:
                hash = entry.attrib["hash"]
                # revisions encode the file name in a href attribute instead of the text
                if "href" in entry.attrib:
                    fname = entry.attrib["href"]
                else:
                    fname = entry.text
                self.download_file(fname + ".pdf", hash, "pdf")
        if self.only_papers:
            for entry in attachments:
                hash = entry.attrib["hash"]
                fname = entry.text
                self.download_file(fname, hash, "attachment")


def main():
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--to"]:
        args["--to"] = args["--to"].format(scriptdir=scriptdir)
    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)
    mirrorer = ACLMirrorer(args)
    for f in args["XMLFILE"]:
        log.info("processing {} ...".format(f))
        mirrorer.download_files(f)
    eprint("\nFiles that could not be downloaded")
    eprint("==================================")
    for elem in mirrorer.not_downloadable:
        eprint(elem)
    eprint("\n\nFiles with checksum mismatch")
    eprint("============================")
    for elem in mirrorer.hash_mismatches:
        eprint(elem)


if __name__ == "__main__":
    main()
