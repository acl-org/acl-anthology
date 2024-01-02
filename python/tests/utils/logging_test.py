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

import logging
from acl_anthology.utils import logging as my_logging


def test_integrated_logging():
    logger = my_logging.get_logger()
    tracker = my_logging.setup_rich_logging()
    logger.addHandler(tracker)
    assert tracker.highest == logging.NOTSET
    logger.warning("A warning message")
    assert tracker.highest == logging.WARNING
    logger.error("An error message")
    assert tracker.highest == logging.ERROR
    logger.warning("A warning message")
    assert tracker.highest == logging.ERROR
