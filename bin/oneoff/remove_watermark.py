#!/usr/bin/env python3

from __future__ import annotations

from typing import BinaryIO, Union
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject

import os

PathOrFile = Union[str, "os.PathLike[str]", BinaryIO]


def remove_margin_watermark_streams(
    src: PathOrFile,
    dst: PathOrFile,
    *,
    marker: str = "Downloaded from http://direct.mit.edu",
    encoding_fallback: str = "latin-1",
) -> int:
    """
    Remove watermark text that is embedded in per-page content streams.

    This targets PDFs where each page's /Contents is either:
      - a single stream, or
      - an array of streams,
    and the watermark appears as literal text in one of those streams (common for
    publisher "Downloaded from ..." margins).

    Strategy:
      - For each page, read each content stream's raw bytes.
      - If the marker substring appears, drop that stream from the /Contents array.
      - If /Contents is a single stream and matches, replace it with an empty stream.

    Returns:
      The number of content streams removed across the document.
    """
    reader = PdfReader(src)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)
    removed = 0

    marker_bytes = marker.encode("utf-8", errors="ignore")

    for page in writer.pages:
        contents = page.get("/Contents")

        # If no contents, just copy page over.
        if contents is None:
            writer.add_page(page)
            continue

        # Normalize to a list of content stream objects.
        if isinstance(contents, (list, ArrayObject)):
            streams = list(contents)
        else:
            streams = [contents]

        kept_streams = []
        page_removed = 0

        for s in streams:
            # pypdf content stream objects support get_data()
            data = s.get_data()
            # Sometimes content streams are not UTF-8; look for marker as bytes first.
            has_marker = marker_bytes in data
            if not has_marker:
                # Fallback: try a permissive decode and search as text (rarely needed).
                try:
                    has_marker = marker in data.decode("utf-8")
                except UnicodeDecodeError:
                    has_marker = marker in data.decode(encoding_fallback, errors="ignore")

            if has_marker:
                page_removed += 1
            else:
                kept_streams.append(s)

        removed += page_removed

        if page_removed == 0:
            # No change
            continue

        # Mutate the page's /Contents appropriately.
        if len(kept_streams) == 0:
            # Replace with empty content stream (keeps page valid).
            page.__setitem__(
                NameObject("/Contents"),
                writer._add_object(writer._create_stream(b"")),
            )
        elif len(kept_streams) == 1:
            page.__setitem__(NameObject("/Contents"), kept_streams[0])
        else:
            page.__setitem__(NameObject("/Contents"), ArrayObject(kept_streams))

    # Write output
    if hasattr(dst, "write"):
        writer.write(dst)  # type: ignore[arg-type]
    else:
        with open(dst, "wb") as f:
            writer.write(f)

    return removed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove margin watermark text from PDF content streams."
    )
    parser.add_argument("src", help="Input PDF file path")
    parser.add_argument("dst", help="Output PDF file path")
    parser.add_argument(
        "--marker",
        default="Downloaded from http://direct.mit.edu",
        help="Marker text to search for in content streams",
    )
    args = parser.parse_args()

    num_removed = remove_margin_watermark_streams(args.src, args.dst, marker=args.marker)
    print(f"Removed {num_removed} content streams containing the marker.")
