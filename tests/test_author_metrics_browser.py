"""Exercise the chart's DOM output with Node, without browser dependencies."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_author_metrics_browser():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the author-metrics browser tests")
    subprocess.run(
        [node, "--test", str(Path(__file__).parent / "javascript/author-metrics.cjs")],
        check=True,
    )
