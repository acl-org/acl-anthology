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

"""Functions providing converters and validators for [attrs](https://www.attrs.org/) classes."""

from __future__ import annotations

import attrs
from attrs import validators
import datetime
from typing import Any, Callable, Optional
import re

from .ids import AnthologyIDTuple


RE_WRAPPED_TYPE = re.compile(r"^([^\[]*)\[(.*)\]$")


def validate_anthology_id_tuple(cls: Any, attr: attrs.Attribute[Any], value: Any) -> None:
    if (
        isinstance(value, tuple)
        and len(value) == 3
        and isinstance(value[0], str)
        and isinstance(value[1], (type(None), str))
        and isinstance(value[2], (type(None), str))
    ):
        return

    raise TypeError(
        f"'{attr.name}' must be AnthologyIDTuple (got {value!r})",
        attr,
        AnthologyIDTuple,
        value,
    )


def auto_validate_types(
    cls: type, fields: list[attrs.Attribute[Any]]
) -> list[attrs.Attribute[Any]]:
    """Add validators to attrs classes based on their type annotations.

    Intended to be used with the `field_transformer` parameter of [`@attrs.define`][attrs.define].

    Supported type annotations:
      - str, int
      - `FileReference` and derived classes
      - `Name`, `NameSpecification`
      - `MarkupText`
      - `Optional[<type>]`
      - `list[<type>]`
      - `tuple[<type>, ...]`

    The purpose of this function is to reduce the need for explicitly adding validators to the classes in `acl_anthology.collections` and `acl_anthology.people.person`.  It does _not_ automatically validate classes _defined_ in `acl_anthology.collections`, as that would lead to circular imports.

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

    def make_validator(field_type: Any) -> Optional[Callable[..., Any]]:
        if not isinstance(field_type, str):
            return None

        # Handle Optional[], list[], etc.
        if (m := RE_WRAPPED_TYPE.match(field_type)) is not None:
            match m.group(1):
                case "Optional":
                    if (inner := make_validator(m.group(2))) is not None:
                        return validators.optional(inner)
                case "dict":
                    dict_parts = m.group(2).split(", ")
                    if (
                        len(dict_parts) == 2
                        and (key_inner := make_validator(dict_parts[0])) is not None
                        and (value_inner := make_validator(dict_parts[1])) is not None
                    ):
                        return validators.deep_mapping(
                            key_validator=key_inner, value_validator=value_inner
                        )
                case "list":
                    if (inner := make_validator(m.group(2))) is not None:
                        return validators.deep_iterable(
                            member_validator=inner,
                            iterable_validator=validators.instance_of(list),
                        )
                case "tuple":
                    tuple_parts = m.group(2).split(", ")
                    # Only tuples of variable length with a single type
                    if (
                        len(tuple_parts) == 2
                        and tuple_parts[1] == "..."
                        and (inner := make_validator(tuple_parts[0])) is not None
                    ):
                        return validators.deep_iterable(
                            member_validator=inner,
                            iterable_validator=validators.instance_of(tuple),
                        )
            # unsupported
            return None

        # Handle known types
        if (type_ := known_types.get(field_type)) is not None:
            return validators.instance_of(type_)
        elif field_type == "AnthologyIDTuple":
            return validate_anthology_id_tuple

        # unsupported
        return None

    results = []
    for field in fields:
        # Don't modify field if validator already defined
        if field.validator is not None:
            results.append(field)
            continue

        if (validator := make_validator(field.type)) is not None:
            results.append(field.evolve(validator=validator))
        else:
            results.append(field)

    return results


def int_to_str(value: Any) -> Any:
    """Convert an int to str, and leave unchanged otherwise.

    Intended to be used as a converter for [attrs.field][].
    """
    if isinstance(value, int):
        return str(value)
    return value


def date_to_str(value: Any) -> Any:
    """Convert a [date][datetime.date] or [datetime][datetime.datetime] object to str (in ISO format), and leave unchanged otherwise.

    Intended to be used as a converter for [attrs.field][].
    """
    if isinstance(value, datetime.date):
        return value.isoformat()
    elif isinstance(value, datetime.datetime):
        return value.date().isoformat()
    return value
