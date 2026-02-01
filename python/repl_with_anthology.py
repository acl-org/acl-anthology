#!/usr/bin/env python3 -i
# -*- coding: utf-8 -*-
#
# Copyright 2024-2026 Marcel Bollmann <marcel@bollmann.me>
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

##############################################################################
# This file is not meant to be run or imported directly, but via
#
#   uv run python -i repl_with_anthology.py
#
# in order to start up a Python REPL where the 'anthology' variable is
# already pre-instantiated with an Anthology object pointing to the data
# folder in this repo.
#
# The `just` command for achieving the same thing is
#
#   just repl
#
##############################################################################

# ruff: noqa
# type: ignore

import sys

print(f"Python {sys.version} on {sys.platform}")

from rich import pretty, inspect, traceback
from rich import print

pretty.install()
_ = traceback.install()
del _

from acl_anthology import Anthology
from acl_anthology.utils.logging import setup_rich_logging

setup_rich_logging(level="INFO")
anthology = Anthology.from_within_repo()
print(f">>> anthology = {anthology}")
