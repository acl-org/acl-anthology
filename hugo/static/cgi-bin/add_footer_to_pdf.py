#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025-2026 Matt Post <post@cs.jhu.edu>
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

"""Add an ACL-style first-page footer and optional page numbers to a PDF.

Footer text supports inline italics with ``<i>…</i>``.

Examples:
    python add_footer_to_pdf.py in.pdf out.pdf \
        "<i>Proceedings … pages 8697–8727</i>\nJuly 27 - August 1, 2025 ©2025 ACL"
    python add_footer_to_pdf.py -p 199 in.pdf out.pdf "…"
"""

import argparse
import io
from pathlib import Path
import re

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# Defaults tuned for ACL footer look
DEFAULT_BOTTOM_MARGIN_PT = 14
DEFAULT_LINE_SPACING = 1.2
DEFAULT_FOOTER_SIZE = 9  # footer text size
DEFAULT_PAGENUM_SIZE = 11  # page number size

FONT_REG = "Times-Roman"
FONT_ITAL = "Times-Italic"

TAG_RE = re.compile(r"(</?i>)")


def parse_inline_italics(text):
    """Yield (text, is_italic) spans from a string with <i>…</i> regions."""
    parts = TAG_RE.split(text)
    italic = False
    for token in parts:
        if token == "<i>":
            italic = True
        elif token == "</i>":
            italic = False
        elif token:
            yield token, italic


def measure_line(pdf_canvas, line, font_size):
    """Total width of a mixed-style line."""
    line_width = 0.0
    for text, is_italic in parse_inline_italics(line):
        font = FONT_ITAL if is_italic else FONT_REG
        line_width += pdf_canvas.stringWidth(text, font, font_size)
    return line_width


def draw_rich_centered(pdf_canvas, page_width, baseline_y, line, font_size):
    """Draw a mixed-style line horizontally centered at a baseline."""
    line_width = measure_line(pdf_canvas, line, font_size)
    cursor_x = (page_width - line_width) / 2.0
    for text, is_italic in parse_inline_italics(line):
        font = FONT_ITAL if is_italic else FONT_REG
        pdf_canvas.setFont(font, font_size)
        pdf_canvas.drawString(cursor_x, baseline_y, text)
        cursor_x += pdf_canvas.stringWidth(text, font, font_size)


def mk_footer_overlay(
    page_width, page_height, text_block, bottom_margin, font_size, line_spacing
):
    """Footer block near bottom: render lines in given order, stacking downward."""
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    lines = text_block.split("\n") if text_block else []
    if not lines:
        pdf_canvas.showPage()
        pdf_canvas.save()
        buffer.seek(0)
        return buffer

    line_height = font_size * line_spacing
    baseline_y = bottom_margin + (len(lines) - 1) * line_height
    for line in lines:
        draw_rich_centered(pdf_canvas, page_width, baseline_y, line, font_size)
        baseline_y -= line_height
    pdf_canvas.showPage()
    pdf_canvas.save()
    buffer.seek(0)
    return buffer


def mk_pagenum_overlay(page_width, page_height, page_number, bottom_margin, font_size):
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    pdf_canvas.setFont(FONT_REG, font_size)
    text = str(page_number)
    text_width = pdf_canvas.stringWidth(text, FONT_REG, font_size)
    text_x = (page_width - text_width) / 2.0
    pdf_canvas.drawString(text_x, bottom_margin, text)
    pdf_canvas.showPage()
    pdf_canvas.save()
    buffer.seek(0)
    return buffer


def process(
    input_pdf,
    output_pdf,
    text_block,
    page_start,
    bottom_margin,
    footer_size,
    pagenum_size,
    line_spacing,
):
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    footer_overlays, page_number_overlays = {}, {}

    for page_index, source_page in enumerate(reader.pages, start=1):
        page = writer.add_page(source_page)
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        displayed_page_number = (
            None if page_start is None else page_start + page_index - 1
        )

        page_number_bottom = bottom_margin
        if page_index == 1 and text_block:
            footer_key = (
                page_width,
                page_height,
                footer_size,
                bottom_margin,
                line_spacing,
                text_block,
            )
            if footer_key not in footer_overlays:
                footer_overlays[footer_key] = PdfReader(
                    mk_footer_overlay(
                        page_width,
                        page_height,
                        text_block,
                        bottom_margin,
                        footer_size,
                        line_spacing,
                    )
                ).pages[0]
            page.merge_page(footer_overlays[footer_key])
            footer_height = len(text_block.split("\n")) * footer_size * line_spacing
            page_number_bottom += footer_height + 0.6 * footer_size

        if displayed_page_number is not None:
            page_number_key = (
                page_width,
                page_height,
                displayed_page_number,
                pagenum_size,
                page_number_bottom,
            )
            if page_number_key not in page_number_overlays:
                page_number_overlays[page_number_key] = PdfReader(
                    mk_pagenum_overlay(
                        page_width,
                        page_height,
                        displayed_page_number,
                        page_number_bottom,
                        pagenum_size,
                    )
                ).pages[0]
            page.merge_page(page_number_overlays[page_number_key])

    with open(output_pdf, "wb") as output_file:
        writer.write(output_file)


def main():
    ap = argparse.ArgumentParser(
        description="Add ACL-like footer (first page) and optional page numbers (all pages)."
    )
    ap.add_argument(
        "--page-number",
        "-p",
        type=int,
        metavar="N",
        help="Enable page numbers starting at N (e.g., -p 5).",
    )
    ap.add_argument(
        "--bottom-margin",
        type=float,
        default=14,
        help="Baseline distance from bottom (pt).",
    )
    ap.add_argument(
        "--footer-size",
        type=float,
        default=DEFAULT_FOOTER_SIZE,
        help="Footer font size (pt).",
    )
    ap.add_argument(
        "--pagenum-size",
        type=float,
        default=DEFAULT_PAGENUM_SIZE,
        help="Page number font size (pt).",
    )
    ap.add_argument(
        "--line-spacing", type=float, default=1.2, help="Footer line spacing multiplier."
    )
    ap.add_argument("input_pdf", type=Path)
    ap.add_argument("output_pdf", type=Path)
    ap.add_argument(
        "text_block",
        nargs="?",
        default="",
        help="Footer text for FIRST page only. Use \\n for newlines. Use <i>…</i> for inline italics.",
    )
    args = ap.parse_args()

    # normalize literal "\n"
    args.text_block = args.text_block.replace("\\n", "\n")

    process(
        args.input_pdf,
        args.output_pdf,
        args.text_block,
        args.page_number,
        args.bottom_margin,
        args.footer_size,
        args.pagenum_size,
        args.line_spacing,
    )


if __name__ == "__main__":
    main()
