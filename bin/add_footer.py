#!/usr/bin/env python3
"""
Add ACL-like footer (first page) and optional page numbers (all pages).
Inline italics with <i>…</i>.

Examples:
    python add_footer.py in.pdf out.pdf \
 "<i>Proceedings … pages 8697–8727</i>\nJuly 27 - August 1, 2025 ©2025 ACL"
    python add_footer.py -p 199 in.pdf out.pdf "…"
    python add_footer.py -p 199 --footer-size 9 --pagenum-size 10 --bottom-margin 14 in.pdf out.pdf "…"

Copyright 2025, Matt Post
"""


import io, re, argparse
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# Defaults tuned for ACL footer look
DEFAULT_BOTTOM_MARGIN_PT = 14
DEFAULT_LINE_SPACING = 1.2
DEFAULT_FOOTER_SIZE = 9       # footer text size
DEFAULT_PAGENUM_SIZE = 11     # page number size

FONT_REG = "Times-Roman"
FONT_ITAL = "Times-Italic"

TAG_RE = re.compile(r"(</?i>)")

def parse_inline_italics(s):
    """Yield (text, is_italic) spans from a string with <i>…</i> regions."""
    parts = TAG_RE.split(s)
    italic = False
    for tok in parts:
        if tok == "<i>":
            italic = True
        elif tok == "</i>":
            italic = False
        elif tok:
            yield tok, italic

def measure_line(c, line, size):
    """Total width of a mixed-style line."""
    w = 0.0
    for txt, it in parse_inline_italics(line):
        font = FONT_ITAL if it else FONT_REG
        w += c.stringWidth(txt, font, size)
    return w

def draw_rich_centered(c, page_w, y, line, size):
    """Draw a mixed-style line centered at y."""
    total_w = measure_line(c, line, size)
    x = (page_w - total_w) / 2.0
    for txt, it in parse_inline_italics(line):
        font = FONT_ITAL if it else FONT_REG
        c.setFont(font, size)
        c.drawString(x, y, txt)
        x += c.stringWidth(txt, font, size)

def mk_footer_overlay(w, h, text_block, bottom_margin, size, line_spacing):
    """Footer block near bottom: render lines in given order, stacking downward."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    lines = text_block.split("\n") if text_block else []
    if not lines:
        c.showPage(); c.save(); buf.seek(0); return buf

    line_h = size * line_spacing
    # Start y so that the FIRST line appears above subsequent lines,
    # with the LAST line's baseline at bottom_margin.
    y = bottom_margin + (len(lines) - 1) * line_h
    for line in lines:
        draw_rich_centered(c, w, y, line, size)
        y -= line_h  # next line goes BELOW
    c.showPage(); c.save(); buf.seek(0)
    return buf

def mk_pagenum_overlay(w, h, page_num, bottom_margin, size):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFont(FONT_REG, size)
    text = str(page_num)
    tw = c.stringWidth(text, FONT_REG, size)
    x = (w - tw) / 2.0
    y = bottom_margin
    c.drawString(x, y, text)
    c.showPage(); c.save(); buf.seek(0)
    return buf


def process(input_pdf, output_pdf, text_block, page_start,
            bottom_margin, footer_size, pagenum_size, line_spacing):
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    footer_cache, pnum_cache = {}, {}

    for idx, page in enumerate(reader.pages, start=1):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        disp_num = None if page_start is None else page_start + idx - 1

        # Page number: SAME bottom margin on every page
        if disp_num is not None:
            nkey = (w, h, disp_num, pagenum_size, bottom_margin)
            if nkey not in pnum_cache:
                pnum_cache[nkey] = PdfReader(
                    mk_pagenum_overlay(w, h, disp_num, bottom_margin, pagenum_size)
                ).pages[0]
            page.merge_page(pnum_cache[nkey])

        # Footer only on first page; place it ABOVE the fixed page number
        if idx == 1 and text_block:
            # raise footer so its LAST line sits above the page number by a small gap
            gap = 0.6 * footer_size
            footer_bottom = bottom_margin + pagenum_size + gap
            fkey = (w, h, "footer", footer_size, footer_bottom, line_spacing, text_block)
            if fkey not in footer_cache:
                footer_cache[fkey] = PdfReader(
                    mk_footer_overlay(w, h, text_block, footer_bottom, footer_size, line_spacing)
                ).pages[0]
            page.merge_page(footer_cache[fkey])

        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)



def main():
    ap = argparse.ArgumentParser(description="Add ACL-like footer (first page) and optional page numbers (all pages).")
    ap.add_argument("--page-number", "-p", type=int, metavar="N",
                        help="Enable page numbers starting at N (e.g., -p 5).")
    ap.add_argument("--bottom-margin", type=float, default=14, help="Baseline distance from bottom (pt).")
    ap.add_argument("--footer-size", type=float, default=DEFAULT_FOOTER_SIZE, help="Footer font size (pt).")
    ap.add_argument("--pagenum-size", type=float, default=DEFAULT_PAGENUM_SIZE, help="Page number font size (pt).")
    ap.add_argument("--line-spacing", type=float, default=1.2, help="Footer line spacing multiplier.")
    ap.add_argument("input_pdf", type=Path)
    ap.add_argument("output_pdf", type=Path)
    ap.add_argument("text_block", nargs="?", default="", help="Footer text for FIRST page only. Use \\n for newlines. Use <i>…</i> for inline italics.")
    args = ap.parse_args()

    # normalize literal "\n"
    args.text_block = args.text_block.replace("\\n","\n")

    process(
        args.input_pdf, args.output_pdf, args.text_block, args.page_number,
        args.bottom_margin, args.footer_size, args.pagenum_size, args.line_spacing,

    )

if __name__ == "__main__":
    main()