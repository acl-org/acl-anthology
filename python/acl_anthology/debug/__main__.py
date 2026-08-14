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

##############################################################################
#
# This file exists to facilitate profiling (timing, memory usage, errors) of
# loading the entire ACL Anthology data.
#
# It can be run with various profiling tools, e.g. Memray:
#
#   uv run memray run -m acl_anthology.debug
#
# It can also be run as a standalone tool with simple statistics from `time`
# and `tracemalloc`:
#
#   uv run python -m acl_anthology.debug -t
#
##############################################################################

import argparse
import gc
import time
import tracemalloc

from .. import Anthology
from ..utils.logging import setup_rich_logging


parser = argparse.ArgumentParser(
    description="Wrapper for executing `Anthology.from_within_repo().load_all()`",
)
parser.add_argument(
    "-t",
    "--trace",
    action="store_true",
    help="track time and memory usage and output results",
)
parser.add_argument(
    "-v",
    "--verbose",
    action="count",
    help="output more log messages (-v to show INFO and WARNING messages, -vv to show DEBUG messages)",
)
args = parser.parse_args()


setup_rich_logging(
    level="ERROR" if args.verbose is None else "INFO" if args.verbose == 1 else "DEBUG"
)

if args.trace:
    tracemalloc.start()
    t0 = time.perf_counter()

anthology = Anthology.from_within_repo().load_all()

if args.trace:
    t1 = time.perf_counter()
    mem_current, mem_peak = tracemalloc.get_traced_memory()

del anthology
gc.collect()

if args.trace:
    t2 = time.perf_counter()
    mem_after_gc, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    from rich.console import Console
    from rich.table import Table

    table = Table(title="Anthology.from_within_repo().load_all()", show_header=False)
    table.add_column("Description", justify="left", no_wrap=True)
    table.add_column("Value", justify="right", style="green")
    table.add_column("Description", justify="left", no_wrap=True)
    table.add_column("Value", justify="right", style="green")

    table.add_row(
        "Time, total",
        f"{t2 - t0:.3f} s",
        "Memory usage, peak",
        f"{mem_peak / 1024 / 1024:.1f} MB",
    )
    table.add_row(
        "Time, for load_all()",
        f"{t1 - t0:.3f} s",
        "Memory usage, after load_all()",
        f"{mem_current / 1024 / 1024:.1f} MB",
    )
    table.add_row(
        "Time, for gc.collect()",
        f"{t2 - t1:.3f} s",
        "Memory usage, after gc.collect()",
        f"{mem_after_gc / 1024 / 1024:.1f} MB",
    )
    print()
    Console().print(table)
