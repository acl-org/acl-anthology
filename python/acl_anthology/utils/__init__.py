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

from .git import clone_or_pull_from_repo
from .ids import build_id, parse_id, AnthologyID
from .latex import latex_encode, latex_convert_quotes
from .logging import setup_rich_logging, get_logger
from .text import remove_extra_whitespace
from .xml import stringify_children


__all__ = [
    "AnthologyID",
    "build_id",
    "clone_or_pull_from_repo",
    "get_logger",
    "latex_encode",
    "latex_convert_quotes",
    "parse_id",
    "remove_extra_whitespace",
    "setup_rich_logging",
    "stringify_children",
]
