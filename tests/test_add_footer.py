import importlib.util
from pathlib import Path

from pypdf import PdfReader, PdfWriter
import pytest


pytest.importorskip("reportlab")

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "add_footer_to_pdf.py"
SPEC = importlib.util.spec_from_file_location("add_footer_to_pdf", SCRIPT)
ADD_FOOTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADD_FOOTER)


def text_positions(page):
    positions = {}

    def record_position(text, _current_matrix, text_matrix, _font, _font_size):
        if text.strip():
            positions[text.strip()] = (text_matrix[4], text_matrix[5])

    page.extract_text(visitor_text=record_position)
    return positions


def test_first_page_number_is_above_footer(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    writer.write(input_pdf)

    ADD_FOOTER.process(
        input_pdf=input_pdf,
        output_pdf=output_pdf,
        text_block="Footer line",
        page_start=10,
        bottom_margin=14,
        footer_size=9,
        pagenum_size=11,
        line_spacing=1.2,
    )

    first_page, second_page = PdfReader(output_pdf).pages
    first_positions = text_positions(first_page)
    second_positions = text_positions(second_page)
    assert first_positions["10"][1] > first_positions["Footer line"][1]
    assert second_positions["11"][1] == pytest.approx(14)
