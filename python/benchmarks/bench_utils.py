# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
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

import re

REPEAT = 20_000
URL_STRINGS = (
    "2020.multilingualbio-1.6",
    "2022.emnlp-industry.56",
    "2023.findings-eacl.197",
    "http://www.lrec-conf.org/proceedings/lrec2000/pdf/374.pdf",
    "https://link.springer.com/chapter/10.1007/3-540-49478-2_33",
)


def detect_url_regex():
    """Detect if string is an external URL via regex."""
    re_detect_protocol = re.compile(r"https?://")
    for _ in range(REPEAT):
        for url in URL_STRINGS:
            re_detect_protocol.match(url) is None


def detect_url_contains_separator():
    """Detect if string is an external URL via testing for '://'."""
    for _ in range(REPEAT):
        for url in URL_STRINGS:
            "://" in url


def detect_url_startswith_protocol():
    """Detect if string is an external URL via testing if it starts with 'http'."""
    for _ in range(REPEAT):
        for url in URL_STRINGS:
            url.startswith("http")


__benchmarks__ = [
    (
        detect_url_regex,
        detect_url_contains_separator,
        "Check URL via regex vs. '://' in string",
    ),
    (
        detect_url_startswith_protocol,
        detect_url_contains_separator,
        "Check URL via .startswith('http') vs. '://' in string",
    ),
]
