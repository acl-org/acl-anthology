#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2025 Matt Post <post@cs.jhu.edu>
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

"""
Takes a list of XML files on STDIN (ideally produced from a `git diff --name-only),
and print links to files that have changed. This is used to create Github-friendly
link previews.

Example usage:

    git diff --name-only master | ./bin/get_changes_from_git_diff.py https://preview.aclanthology.org/BRANCH

The argument to the script is the URL root for the preview.

"""

import sys
import argparse
import logging
from pathlib import PurePosixPath
from typing import Iterable

from acl_anthology import Anthology


def changed_links(
    filepaths: Iterable[str], url_root: str, anthology: Anthology | None = None
) -> list[str]:
    """Describe changed content, ignoring XML templates and test fixtures."""
    changeset = []
    for filepath in filepaths:
        filepath = filepath.rstrip()
        path = PurePosixPath(filepath)
        if path.parent == PurePosixPath("data/xml") and path.suffix == ".xml":
            if anthology is None:
                anthology = Anthology.from_within_repo(suppress_warnings=True)
            collection = anthology.get_collection(path.stem)
            if collection is None:
                logging.warning(
                    "Changed collection %s is absent; omitting preview links", path.stem
                )
                continue
            for volume in collection.volumes():
                changeset.append(
                    f"[{volume.full_id}]({url_root}/volumes/{volume.full_id})"
                )
        elif filepath.startswith("hugo/content/faq"):
            change = f"[FAQ]({url_root}/faq)"
            if change not in changeset:
                changeset.append(change)
        elif filepath.startswith("hugo/content/info"):
            changeset.append(f"[Info: {path.stem}]({url_root}/info/{path.stem})")
    if len(changeset) > 50:
        return changeset[:50] + [f"(plus {len(changeset) - 50} more...)"]
    return changeset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url_root")
    args = parser.parse_args()
    print(", ".join(changed_links(sys.stdin, args.url_root)))


if __name__ == "__main__":
    main()
