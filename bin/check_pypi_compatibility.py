#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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
"""Checks whether the version of `acl_anthology` currently published on PyPI
can still load and validate the data currently checked into this repo.

This is meant to catch the case where `data/` has evolved (new schema
elements, stricter name conventions, etc.) in a way that the latest
*released* library version doesn't know how to handle -- i.e. exactly what a
user who runs `pip install acl-anthology` and points it at this repo would
experience.

Because of this, it deliberately does NOT import the local `python/` package
under development; it is meant to be run against an isolated environment that
has installed `acl-anthology` from PyPI, e.g.:

    uv run --no-project --isolated --with acl-anthology bin/check_pypi_compatibility.py

Both flags matter: without `--no-project`, uv would resolve `acl-anthology`
via this repo's workspace source override and simply re-test the local
checkout; without `--isolated`, uv may still reuse an ambient `.venv` (e.g.
one left behind by an earlier `uv sync`/`uv run` in the same working tree)
instead of installing a clean copy from PyPI.

Only uses the library's public API, per this repo's usual convention for
scripts that touch Anthology data.
"""

import importlib.metadata
import sys
import traceback
from pathlib import Path

from acl_anthology import Anthology

# This script lives in bin/, so its parent's parent is the repo root -- this
# must NOT rely on Anthology.from_within_repo(), which discovers the repo
# root from the *installed* acl_anthology package's own location, not from
# this script or the current working directory.
DATADIR = Path(__file__).resolve().parent.parent / "data"


def main() -> int:
    version = importlib.metadata.version("acl-anthology")
    print(f"Testing acl-anthology=={version} (from PyPI) against {DATADIR}")

    try:
        anthology = Anthology(datadir=DATADIR, verbose=False)
        anthology.load_all()
        for collection in anthology.collections.values():
            collection.validate_schema()
        for person in anthology.people.values():
            for name in person.names:
                name.is_valid(error=True)
    except Exception:
        print(
            f"\nacl-anthology=={version} FAILED to load/validate the current data/:\n",
            file=sys.stderr,
        )
        traceback.print_exc()
        return 1

    print(
        f"acl-anthology=={version} successfully loaded and validated the current data/."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
