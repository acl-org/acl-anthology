# Copyright 2023-2025 Marcel Bollmann <marcel@bollmann.me>
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

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .people import Name, NameSpecification
    from .utils.ids import AnthologyIDTuple

if sys.version_info >= (3, 11):

    class AnthologyException(Exception):
        """Base class from which all other exceptions defined here inherit."""

        def __init__(self, msg: str):
            super().__init__(msg)

else:

    class AnthologyException(Exception):
        def __init__(self, msg: str):
            super().__init__(msg)
            self.__notes__: list[str] = []

        def add_note(self, note: str) -> None:
            self.__notes__.append(note)


class AmbiguousNameError(AnthologyException):
    """Raised when an ambiguous name would need an explicit and unique ID, but does not have one.

    Attributes:
        name (Name): The name that raised the error.
    """

    def __init__(self, name: Name, message: str) -> None:
        super().__init__(message)
        self.name = name
        self.add_note("Did you forget to add an explicit/unique ID to this name?")


class AnthologyDuplicateIDError(AnthologyException, ValueError):
    """Raised when trying to set an ID or create an item with an ID that already exists.

    Attributes:
        value: The value that raised the error.  Can be any unique identifier, e.g. an Anthology ID, or a bibkey.
    """

    def __init__(self, value: object, message: str) -> None:
        super().__init__(message)
        self.value = value


class AnthologyInvalidIDError(AnthologyException, ValueError):
    """Raised when a function gets an ID that is not a valid Anthology ID, or not valid in the given context (e.g. a full ID where only a paper ID was expected).

    Attributes:
        value: The value that raised the error.
    """

    def __init__(self, value: object, message: str) -> None:
        super().__init__(message)
        self.value = value


class AnthologyXMLError(AnthologyException, ValueError):
    """Raised when an unsupported tag is encountered while parsing an Anthology XML file.

    Attributes:
        parent (AnthologyIDTuple): The Anthology ID of the parent object in which the error occurred.
        tag (str): The name of the unsupported tag.
    """

    def __init__(self, parent: AnthologyIDTuple, tag: str, message: str) -> None:
        super().__init__(message)
        self.parent = parent
        self.tag = tag


class NameIDUndefinedError(AnthologyException):
    """Raised when an author ID was requested that is not defined.

    This can happen when an `<author>` or `<editor>` was used with an ID which was not defined in `name_variants.yaml`, or when trying to look up a NameSpecification that does not correspond to any Person in the PersonIndex.

    Attributes:
        name_spec (NameSpecification): The name specification that raised the error.
    """

    def __init__(self, name_spec: NameSpecification, message: str) -> None:
        super().__init__(message)
        self.name_spec = name_spec


class SchemaMismatchWarning(UserWarning):
    """Raised when the data directory contains a different XML schema as this library.

    This typically means that either:

    - The data directory is outdated, and needs to be synced with the official Anthology data.
    - This library needs to be updated.
    """

    def __init__(self) -> None:
        super().__init__(
            "Data directory contains a different schema.rnc as this library; "
            "you might need to update the data or the acl-anthology library."
        )
