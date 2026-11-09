import re
from pathlib import Path

import pytest


HTACCESS = Path(__file__).parents[1] / "hugo" / "static" / ".htaccess"


def video_destination(filename):
    for line in HTACCESS.read_text().splitlines():
        fields = line.split()
        if len(fields) != 4 or fields[0] != "RewriteRule":
            continue
        _, pattern, destination, flags = fields
        if not destination.startswith("anthology-files/videos/"):
            continue
        match = re.fullmatch(
            pattern, filename, flags=re.IGNORECASE if "NC" in flags else 0
        )
        if match:
            return re.sub(
                r"\$(\d+)",
                lambda token: match.group(int(token[1])) or "",
                destination,
            )
    return None


@pytest.mark.parametrize("extension", ("mp4", "mov", "m4v", "webm"))
@pytest.mark.parametrize("part", ("", ".1", ".12"))
@pytest.mark.parametrize(
    ("paper_id", "directory"),
    (("2025.acl-long.1", "acl"), ("N13-1001", "N")),
)
def test_video_urls_resolve_to_exact_filenames(extension, part, paper_id, directory):
    filename = f"{paper_id}{part}.{extension}"
    assert video_destination(filename) == f"anthology-files/videos/{directory}/{filename}"


@pytest.mark.parametrize(
    "filename",
    (
        "2025.acl-long.1.pdf",
        "2025.acl-long.1.mp3",
        "2025.acl-long.1.underline.mp4",
        "2025.acl-long.mp4",
        "../2025.acl-long.1.mp4",
    ),
)
def test_non_video_urls_do_not_match_video_rules(filename):
    assert video_destination(filename) is None
