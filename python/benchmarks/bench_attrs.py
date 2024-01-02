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

import attrs
from attrs import define, field


REPEAT = 100_000
URL = "http://www.lrec-conf.org/proceedings/lrec2000/pdf/374.pdf"


class UrlWithoutAttrs:
    def __init__(self, url: str) -> None:
        self.url = url


@define
class UrlWithoutValidation:
    url: str


@define
class UrlWithValidation:
    url: str = field()

    @url.validator
    def noop(self, _attribute, _value):
        pass


def vanilla_class_without_validation():
    """Instantiate a regular class."""
    for _ in range(REPEAT):
        UrlWithoutAttrs(URL)


def attrs_class_without_validation():
    """Instantiate a class without attribute validation."""
    for _ in range(REPEAT):
        UrlWithoutValidation(URL)


def attrs_class_with_validation():
    """Instantiate a class with attribute validation."""
    for _ in range(REPEAT):
        UrlWithValidation(URL)


def attrs_class_with_validation_disabled():
    """Instantiate a class that has attribute validation, but disabled."""
    with attrs.validators.disabled():
        for _ in range(REPEAT):
            UrlWithValidation(URL)


__benchmarks__ = [
    (
        vanilla_class_without_validation,
        attrs_class_without_validation,
        "attrs: Vanilla class vs. attrs class",
    ),
    (
        attrs_class_with_validation,
        attrs_class_without_validation,
        "attrs: Attribute validation vs. no validation",
    ),
    (
        attrs_class_with_validation_disabled,
        attrs_class_without_validation,
        "attrs: Attribute validation disabled vs. no validation",
    ),
]
