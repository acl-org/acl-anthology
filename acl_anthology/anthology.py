from pathlib import Path
#from .papers import PaperIndex


class Anthology:
    def __init__(self, datadir):
        if not Path(datadir).is_dir():
            raise ValueError(f"Not a directory: {datadir}")  # TODO exception type

        self._datadir = datadir
        #self.papers = PaperIndex(self)

    @property
    def datadir(self):
        return self._datadir
