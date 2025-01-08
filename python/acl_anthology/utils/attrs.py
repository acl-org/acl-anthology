# Copyright 2025 Marcel Bollmann <marcel@bollmann.me>
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

from __future__ import annotations

import attrs
from attrs import validators
from typing import Any, cast
import re


RE_WRAPPED_TYPE = re.compile(r"^([^\[]*)\[(.*)\]$")


def auto_validate_types(
    cls: type, fields: list[attrs.Attribute[Any]]
) -> list[attrs.Attribute[Any]]:
    """Adds validators to attrs classes based on their type annotations.

    Supported type annotations are:
      - str, int
      - FileReference and derived classes
      - Name, NameSpecification
      - MarkupText

    See also: <https://www.attrs.org/en/stable/extending.html#transform-fields>
    """
    from ..files import (
        FileReference,
        PDFReference,
        PDFThumbnailReference,
        AttachmentReference,
        EventFileReference,
        VideoReference,
        PapersWithCodeReference,
    )
    from ..people import Name, NameSpecification
    from ..text import MarkupText

    known_types = {
        t.__name__: t
        for t in {
            str,
            int,
            FileReference,
            PDFReference,
            PDFThumbnailReference,
            AttachmentReference,
            EventFileReference,
            VideoReference,
            PapersWithCodeReference,
            MarkupText,
            Name,
            NameSpecification,
        }
    }

    results = []
    for field in fields:
        if field.validator is not None:
            results.append(field)
            continue

        wrapper: Any = None
        validator: Any = None
        field_type = cast(str, field.type)

        # Handle Optional[], list[], tuple[]
        if (
            isinstance(field_type, str)
            and (m := RE_WRAPPED_TYPE.match(field_type)) is not None
        ):
            field_type = m.group(2)
            match m.group(1):
                case "Optional":
                    wrapper = validators.optional
                case "list":
                    wrapper = lambda x: validators.deep_iterable(  # noqa: E731
                        member_validator=x,
                        iterable_validator=validators.instance_of(list),
                    )
                case "tuple":
                    wrapper = lambda x: validators.deep_iterable(  # noqa: E731
                        member_validator=x,
                        iterable_validator=validators.instance_of(tuple),
                    )
                case _:
                    # unsupported
                    results.append(field)
                    continue

        # Handle known types
        if (type_ := known_types.get(field_type)) is not None:
            validator = validators.instance_of(type_)
        else:
            # unsupported
            results.append(field)
            continue

        # Was type wrapped?
        if wrapper:
            validator = wrapper(validator)

        results.append(field.evolve(validator=validator))

    for field in results:
        if field.validator is None:
            print(
                f"Did not add auto-validator to field '{field.name}' with type annotation '{field.type}'"
            )

    return results


def maybe_int_to_str(value: Any) -> Any:
    if isinstance(value, int):
        return str(value)
    return value
