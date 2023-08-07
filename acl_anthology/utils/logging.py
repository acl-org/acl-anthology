# Copyright 2023 Marcel Bollmann <marcel@bollmann.me>
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

"""Functions for logging."""

import logging
from ..config import config


def get_logger() -> logging.Logger:
    return logging.getLogger(config.get("logger_name"))


def setup_rich_logging(**kwargs) -> None:  # type: ignore
    from rich.logging import RichHandler

    log_config = dict(
        level="NOTSET",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[],
    )
    log_config.update(kwargs)
    log_config["handlers"].append(RichHandler())  # type: ignore
    logging.basicConfig(**log_config)  # type: ignore
