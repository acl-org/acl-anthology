from lxml import etree
from pathlib import Path

from ..logging import log
from ..utils import deconstruct_anthology_id


class PaperIndex:
    def __init__(self, anthology):
        self._anthology = anthology
        self.collections = {}

        self._find_collections()

    def get(self, full_id):
        collection_id, volume_id, paper_id = deconstruct_anthology_id(full_id)
        collection = self.collections[collection_id]
        if not collection["volumes"]:
            self._parse_xml(collection["path"])

    def _find_collections(self):
        """Finds all XML data files and indexes them by their collection ID."""
        for xmlpath in Path(self._anthology.datadir).glob("xml/*.xml"):
            collection_id = xmlpath.name[:-4]
            self.collections[collection_id] = {
                "path": xmlpath,
                "volumes": {},
            }

    def _parse_xml(self, filename):
        log.debug(f"Parsing XML data file: {filename}")
        tree = etree.parse(filename)
        root = tree.getroot()
