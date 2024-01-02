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

"""Functions for logging."""

import logging
from rich.logging import RichHandler
from typing import cast
from ..config import config


def get_logger() -> logging.Logger:
    """
    Returns:
        A library-specific logger instance.
    """
    return logging.getLogger(config.get("logger_name"))


class SeverityTracker(logging.Handler):
    """Tracks the highest log-level that was sent to the logger.

    If this class is added as a log handler, it can be used to check if any errors or exceptions were logged.

    Attributes:
        highest (int): The highest log-level that was sent to the logger.
    """

    def __init__(self, level: int = logging.NOTSET) -> None:
        super().__init__(level=level)
        self.highest: int = logging.NOTSET

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno > self.highest:
            self.highest = record.levelno


def setup_rich_logging(**kwargs: object) -> SeverityTracker:
    """Set up a logger that uses rich markup and severity tracking.

    This function is intended to be called in a script. It calls [logging.basicConfig][] and is therefore not executed by default, as applications may wish to setup their loggers differently.

    Parameters:
        **kwargs: Any keyword argument will be forwarded to [logging.basicConfig][].  If logging handlers are defined here, they will be preserved in addition to the handlers added by this function.

    Returns:
        The severity tracker, so that it can be used to check the highest emitted log level.
    """
    log_config: dict[str, object] = dict(
        level="NOTSET",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[],
    )
    log_config.update(kwargs)
    tracker = SeverityTracker()
    cast(list[logging.Handler], log_config["handlers"]).extend([RichHandler(), tracker])
    logging.basicConfig(**log_config)  # type: ignore
    logging.captureWarnings(True)
    return tracker
