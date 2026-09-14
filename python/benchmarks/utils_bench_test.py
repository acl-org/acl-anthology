# Copyright 2023-2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Cheapest way to detect whether a string looks like an external URL."""

import re
import pytest

URL_STRINGS = (
    "2020.multilingualbio-1.6",
    "2022.emnlp-industry.56",
    "2023.findings-eacl.197",
    "http://www.lrec-conf.org/proceedings/lrec2000/pdf/374.pdf",
    "https://link.springer.com/chapter/10.1007/3-540-49478-2_33",
)

RE_DETECT_PROTOCOL = re.compile(r"https?://")


def detect_via_regex():
    return [RE_DETECT_PROTOCOL.match(url) is not None for url in URL_STRINGS]


def detect_via_contains_separator():
    return ["://" in url for url in URL_STRINGS]


def detect_via_startswith_protocol():
    return [url.startswith("http") for url in URL_STRINGS]


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "detect_fn",
    [detect_via_regex, detect_via_contains_separator, detect_via_startswith_protocol],
    ids=["regex", "contains-separator", "startswith"],
)
def test_url_detection(benchmark, detect_fn):
    benchmark(detect_fn)
