"""Add comments with URLs to all XML files.

This is a separate script because...
- `collection.save(minimal_diff=True)` would not write out the comments, because the files without comments are functionally equivalent to those with comments, so the minimal-diff algorithm simply uses the old files.
- `collection.save(minimal_diff=False)` would write out the comments, but also make lots of other spurious changes that the minimal-diff algorithm is supposed to avoid.
"""

from acl_anthology import Anthology
from acl_anthology.utils import xml
from lxml import etree
from pathlib import Path
from rich.progress import track


def add_comments(collection):
    collection.load()

    root, volume = None, None
    for _, element in etree.iterparse(
        collection.path,
        tag=("meta", "frontmatter", "paper", "volume", "event", "collection"),
        remove_comments=True,  # the only comments should be the ones we insert here
    ):
        if element.tag == "collection":
            root = element
        elif (
            element.tag == "meta"
            and (parent := element.getparent()) is not None
            and parent.tag != "event"
        ):
            volume = collection[element.getparent().get("id")]
        elif element.tag == "volume":
            element.insert(0, etree.Comment(volume.web_url))
        elif element.tag in ("paper", "frontmatter"):
            pid = element.get("id") if element.tag == "paper" else "0"
            paper = volume[pid]
            element.insert(0, etree.Comment(paper.web_url))
        elif element.tag == "event":
            event = collection.get_event()
            element.insert(0, etree.Comment(event.web_url))

    xml.indent(root)
    with open(collection.path, "wb") as f:
        f.write(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))


if __name__ == "__main__":
    test_dir = (
        Path(__file__).parent.resolve().parent.parent
        / "python"
        / "tests"
        / "data"
        / "anthology"
    )
    print("Adding comments in test data folder...")
    test_anthology = Anthology(datadir=test_dir)
    for collection in test_anthology.collections.values():
        add_comments(collection)

    anthology = Anthology.from_within_repo()
    for collection in track(
        anthology.collections.values(), description="Adding comments..."
    ):
        add_comments(collection)
