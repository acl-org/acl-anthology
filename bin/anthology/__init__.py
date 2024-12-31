# ruff: noqa: F401
from .anthology import Anthology
from .people import PersonName
from .papers import Paper
from .volumes import Volume

import warnings

warnings.warn(
    """Your code uses the legacy Anthology library.  Consider migrating to acl-anthology-py <https://acl-anthology-py.readthedocs.io/>""",
    FutureWarning,
    stacklevel=2,
)
