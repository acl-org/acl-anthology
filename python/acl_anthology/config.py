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

"""Global configuration settings."""

from attrs import define
from omegaconf import OmegaConf
from platformdirs import PlatformDirs


@define
class DefaultConfig:
    url_prefix: str = "${oc.env:ANTHOLOGY_PREFIX,https://aclanthology.org}"
    """Prefix for all remote URLs. Can also be overridden with the environment variable `ANTHOLOGY_PREFIX`."""

    paper_page_template: str = "${url_prefix}/{}/"
    """URL formatting template for paper landing pages."""

    pdf_location_template: str = "${url_prefix}/{}.pdf"
    """URL formatting template for paper PDFs."""

    pdf_thumbnail_location_template: str = "${url_prefix}/thumb/{}.jpg"
    """URL formatting template for paper thumbnail images."""

    attachment_location_template: str = "${url_prefix}/attachments/{}"
    """URL formatting template for paper attachments."""

    event_location_template: str = "${url_prefix}/{}"
    """URL formatting template for event-related files."""

    video_location_template: str = "${url_prefix}/{}"
    """URL formatting template for videos."""

    logger_name: str = "acl-anthology"
    """Name of logger to which the library sends log messages."""

    disable_gc: bool = True
    """If True, disables garbage collection while parsing XML files and building indices.  This typically results in a considerable speed-up, but if it happens to cause problems, it can be disabled here."""


config = OmegaConf.structured(DefaultConfig)
"""A [structured configuration instance](https://omegaconf.readthedocs.io/en/latest/structured_config.html) that is used by all `acl_anthology` classes."""

dirs = PlatformDirs("acl-anthology-py")
"""A [PlatformDirs instance](https://platformdirs.readthedocs.io/en/latest/api.html#platformdirs) that returns platform-specific directories for storing data."""
