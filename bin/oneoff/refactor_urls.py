# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Refactors <url> tags in the XML to the new schema."""

from acl_anthology.utils import ids, xml
from lxml import etree
from pathlib import Path
from rich import print
from rich.progress import track


def refactor_urls(collection):
    tree = etree.parse(collection)
    cid, vid, pid = None, None, None
    for event, element in etree.iterwalk(
        tree,
        tag=("collection", "volume", "paper", "url"),
        events=("start", "end"),
    ):
        if event == "start":
            if element.tag == "collection":
                cid = element.get("id")
                vid, pid = None, None
            elif element.tag == "volume":
                vid = element.get("id")
                pid = None
            elif element.tag == "paper":
                pid = element.get("id")
        elif event == "end" and element.tag == "url" and element.get("hash") is not None:
            value = element.text
            if element.getparent().tag == "frontmatter":
                pid = "0"
            item_id = ids.build_id(cid, vid, pid)
            if value != item_id:
                print(
                    f"[bold red]ERROR:[/] {item_id} has {etree.tostring(element, encoding='UTF-8').strip()}"
                )
            else:
                element.tag = "pdf"
                element.text = None

    root = tree.getroot()
    xml.indent(root)
    with open(collection, "wb") as f:
        f.write(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))


if __name__ == "__main__":
    test_dir = (
        Path(__file__).parent.resolve().parent.parent
        / "python"
        / "tests"
        / "data"
        / "anthology"
        / "xml"
    )
    print("Refactoring URLs in test data folder...")
    for collection in test_dir.glob("*.xml"):
        refactor_urls(collection)

    main_dir = Path(__file__).parent.resolve().parent.parent / "data" / "xml"
    for collection in track(
        list(main_dir.glob("*.xml")), description="Refactoring URLs..."
    ):
        refactor_urls(collection)
