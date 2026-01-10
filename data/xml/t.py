#!/usr/bin/env python3
"""
Update <url hash="...">PAPER</url> lines in 2025.emnlp.xml using /tmp/new_urls.txt.

Behavior:
- Entries from /tmp/new_urls.txt are consumed in order.
- When a <url ...>PAPER</url> is found in 2025.emnlp.xml:
    * If PAPER matches the next entry from new_urls.txt:
        - replace only hash="..."
        - advance new_urls iterator
    * If PAPER does NOT match:
        - leave the line unchanged
        - do NOT advance the iterator
- Extra entries in new_urls.txt are ignored.
- Missing entries in new_urls.txt simply result in no replacement.

Writes 2025.emnlp.xml in place and also writes 2025.emnlp.xml.bak.
"""

from pathlib import Path
import re

NEW_URLS = Path("/tmp/new_urls.txt")
XML_FILE = Path("2025.emnlp.xml")
BACKUP = XML_FILE.with_suffix(XML_FILE.suffix + ".bak")

NEW_RE = re.compile(r'<url\b[^>]*\bhash="([^"]+)"[^>]*>\s*([^<\s]+)\s*</url>')
XML_URL_RE = re.compile(r'^(\s*)<url\b[^>]*\bhash="([^"]+)"[^>]*>\s*([^<\s]+)\s*</url>\s*$')

def load_new(path: Path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = NEW_RE.search(line)
        if m:
            out.append((m.group(2), m.group(1)))  # (paper, hash)
    return out

def replace_hash(line: str, new_hash: str) -> str:
    return re.sub(r'\bhash="[^"]*"', f'hash="{new_hash}"', line, count=1)

def main():
    new = load_new(NEW_URLS)
    it = iter(new)
    cur = next(it, None)

    lines = XML_FILE.read_text(encoding="utf-8").splitlines(True)
    out = []
    replaced = 0

    for line in lines:
        m = XML_URL_RE.match(line.rstrip("\n"))
        if not m or cur is None:
            out.append(line)
            continue

        paper = m.group(3)
        exp_paper, new_hash = cur

        if paper == exp_paper:
            out.append(replace_hash(line, new_hash))
            replaced += 1
            cur = next(it, None)
        else:
            out.append(line)

    # backup then write
    BACKUP.write_text(XML_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    XML_FILE.write_text("".join(out), encoding="utf-8")
    print(f"Replaced {replaced} <url> hashes.")

if __name__ == "__main__":
    main()

