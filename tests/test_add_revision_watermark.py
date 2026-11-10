import importlib.util
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, RectangleObject, TextStringObject
import pytest


pytest.importorskip("reportlab")

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "add_revision.py"
SPEC = importlib.util.spec_from_file_location("add_revision", SCRIPT)
ADD_REVISION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADD_REVISION)


def test_revision_watermark_preserves_pages_and_marks_first_page(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    writer.write(input_pdf)

    ADD_REVISION.add_revision_watermark(
        input_pdf,
        output_pdf,
        anth_id="P19-1001",
        revision_id=2,
        date="2026-08-14",
    )

    pages = PdfReader(output_pdf).pages
    assert len(pages) == 2
    assert "ACL Anthology ID P19-1001 / revision 2 / 14 Aug 2026" in (
        pages[0].extract_text()
    )
    assert pages[1].extract_text() == ""


def test_revision_watermark_preserves_links_to_indirect_page_boxes(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    writer.add_named_destination("second-page", 1)
    writer.add_annotation(
        0,
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Link"),
                NameObject("/Rect"): RectangleObject((0, 0, 100, 100)),
                NameObject("/A"): DictionaryObject(
                    {
                        NameObject("/S"): NameObject("/GoTo"),
                        NameObject("/D"): TextStringObject("second-page"),
                    }
                ),
            }
        ),
    )
    box = writer._add_object(RectangleObject((0, 0, 612, 792)))
    for page in writer.pages:
        page[NameObject("/MediaBox")] = box
    writer.write(input_pdf)

    ADD_REVISION.add_revision_watermark(
        input_pdf,
        output_pdf,
        anth_id="P19-1001",
        revision_id=2,
        date="2026-08-14",
    )

    reader = PdfReader(output_pdf)
    assert len(reader.pages) == 2
    assert list(reader.pages[1].mediabox) == [0, 0, 612, 792]
    assert (
        reader.get_destination_page_number(reader.named_destinations["second-page"]) == 1
    )
    assert len(reader.pages[0].get("/Annots")) == 1
    assert "ACL Anthology ID P19-1001 / revision 2 / 14 Aug 2026" in (
        reader.pages[0].extract_text()
    )
