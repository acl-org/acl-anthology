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

from acl_anthology import config
from acl_anthology.files import PDFReference


def test_pdf_reference_remote():
    name = "https://some-external-server.com/paper.pdf"
    ref = PDFReference(name)
    assert ref.url == name


def test_pdf_reference_internal():
    name = "2023.venue-volume.222"
    config.pdf_location_template = "https://my-server.com/{}.pdf"
    ref = PDFReference(name)
    assert ref.url == "https://my-server.com/2023.venue-volume.222.pdf"
