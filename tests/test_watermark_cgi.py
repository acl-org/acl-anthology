import os
from pathlib import Path
import subprocess
import sys


CGI_SCRIPT = (
    Path(__file__).resolve().parents[1] / "hugo" / "static" / "cgi-bin" / "watermark.cgi"
)
BOUNDARY = "acl-anthology-watermark-test"


def make_multipart_body(
    footer_text="",
    page_start="",
    pdf_data=b"%PDF-1.4\n%%EOF\n",
    layout_fields=None,
):
    parts = [
        (
            'Content-Disposition: form-data; name="pdf"; filename="paper.pdf"\r\n'
            "Content-Type: application/pdf",
            pdf_data,
        ),
        ('Content-Disposition: form-data; name="footer_text"', footer_text.encode()),
    ]
    if page_start:
        parts.append(
            ('Content-Disposition: form-data; name="page_start"', page_start.encode())
        )
    for name, value in (layout_fields or {}).items():
        parts.append(
            (f'Content-Disposition: form-data; name="{name}"', str(value).encode())
        )

    body = bytearray()
    for headers, value in parts:
        body.extend(f"--{BOUNDARY}\r\n{headers}\r\n\r\n".encode())
        body.extend(value)
        body.extend(b"\r\n")
    body.extend(f"--{BOUNDARY}--\r\n".encode())
    return bytes(body)


def run_cgi(body=b"", **environment_overrides):
    environment = os.environ.copy()
    environment.update(environment_overrides)
    if body:
        environment["CONTENT_LENGTH"] = str(len(body))
        environment["CONTENT_TYPE"] = f"multipart/form-data; boundary={BOUNDARY}"
    return subprocess.run(
        [sys.executable, str(CGI_SCRIPT)],
        input=body,
        capture_output=True,
        env=environment,
        check=False,
    )


def test_non_post_request_returns_method_not_allowed():
    result = run_cgi(REQUEST_METHOD="GET")

    assert result.returncode == 0, result.stderr.decode()
    response = result.stdout.decode()
    assert "Status: 405 Method Not Allowed" in response
    assert "Allow: POST" in response


def test_post_parses_multipart_and_cleans_up(tmp_path):
    processor = tmp_path / "add_footer_to_pdf.py"
    processor.write_text(
        """from pathlib import Path
import sys

input_pdf, output_pdf, footer = sys.argv[-3:]
payload = Path(input_pdf).read_bytes()
footer_comment = footer.replace("\\n", "|").encode("cp1252")
options = "|".join(sys.argv[1:-3]).encode()
Path(output_pdf).write_bytes(
    payload + b"% options=" + options + b"; footer=" + footer_comment
)
"""
    )
    temp_root = tmp_path / "requests"
    temp_root.mkdir()

    result = run_cgi(
        make_multipart_body(
            "First line\nSecond line",
            "7",
            layout_fields={"bottom_margin": 18, "footer_size": 10},
        ),
        REQUEST_METHOD="POST",
        WATERMARK_ADD_FOOTER=str(processor),
        TMPDIR=str(temp_root),
    )

    assert result.returncode == 0, result.stderr.decode()
    headers, output_pdf = result.stdout.split(b"\r\n\r\n", 1)
    assert b"Content-Type: application/pdf" in headers
    assert b"Content-Disposition: attachment" in headers
    assert output_pdf.startswith(b"%PDF-1.4")
    assert b"--bottom-margin|18|--footer-size|10" in output_pdf
    assert output_pdf.endswith(b"; footer=First line|Second line")
    assert list(temp_root.iterdir()) == []


def test_post_rejects_unsupported_footer_markup():
    result = run_cgi(
        make_multipart_body("<script>alert(1)</script>"),
        REQUEST_METHOD="POST",
    )

    assert result.returncode == 0, result.stderr.decode()
    response = result.stdout.decode()
    assert "Status: 400 Bad Request" in response
    assert "Only <i> and </i> markup is supported." in response


def test_post_rejects_out_of_range_layout_value():
    result = run_cgi(
        make_multipart_body(layout_fields={"bottom_margin": 500}),
        REQUEST_METHOD="POST",
    )

    assert result.returncode == 0, result.stderr.decode()
    response = result.stdout.decode()
    assert "Status: 400 Bad Request" in response
    assert "Bottom margin must be between 0 and 72." in response


def test_post_rejects_no_op_request():
    result = run_cgi(make_multipart_body(), REQUEST_METHOD="POST")

    assert result.returncode == 0, result.stderr.decode()
    response = result.stdout.decode()
    assert "Status: 400 Bad Request" in response
    assert "Enter footer text or a starting page number." in response


def test_processor_failure_cleans_up_and_hides_diagnostic(tmp_path):
    processor = tmp_path / "add_footer_to_pdf.py"
    processor.write_text(
        """import sys

print("internal processor detail", file=sys.stderr)
raise SystemExit(1)
"""
    )
    temp_root = tmp_path / "requests"
    temp_root.mkdir()

    result = run_cgi(
        make_multipart_body(footer_text="Footer"),
        REQUEST_METHOD="POST",
        WATERMARK_ADD_FOOTER=str(processor),
        TMPDIR=str(temp_root),
    )

    assert result.returncode == 0
    response = result.stdout.decode()
    assert "Status: 500 Internal Server Error" in response
    assert "Could not process the PDF." in response
    assert "internal processor detail" not in response
    assert "internal processor detail" in result.stderr.decode()
    assert list(temp_root.iterdir()) == []
