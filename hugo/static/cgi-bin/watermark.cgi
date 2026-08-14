#!/opt/venv/watermark/bin/python3
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

"""CGI service for adding an ACL-style footer and page numbers to a PDF."""

from collections import defaultdict
from email import policy
from email.message import Message
from email.parser import BytesParser
from http import HTTPStatus
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata


MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_PDF_BYTES + 64 * 1024
MAX_MULTIPART_BOUNDARY_CHARS = 200
MAX_FORM_PARTS = 7
MAX_FOOTER_CHARS = 2_000
MAX_FOOTER_LINES = 8
MAX_PAGE_NUMBER = 1_000_000
ITALIC_TAG_RE = re.compile(r"</?i>")
LAYOUT_OPTIONS = {
    "bottom_margin": ("--bottom-margin", "Bottom margin", 0, 72),
    "footer_size": ("--footer-size", "Footer font size", 6, 18),
    "page_number_size": ("--pagenum-size", "Page number font size", 6, 18),
    "line_spacing": ("--line-spacing", "Footer line spacing", 1, 2),
}


class RequestError(Exception):
    def __init__(self, status: HTTPStatus, message: str, headers=()):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers


def fail(status: HTTPStatus, message: str, headers=()):
    raise RequestError(status, message, headers)


def write_error(error: RequestError):
    body = (error.message + "\n").encode("utf-8")
    headers = [
        f"Status: {error.status.value} {error.status.phrase}",
        "Content-Type: text/plain; charset=utf-8",
        "X-Content-Type-Options: nosniff",
        "Cache-Control: no-store",
        f"Content-Length: {len(body)}",
        *(f"{name}: {value}" for name, value in error.headers),
    ]
    sys.stdout.buffer.write(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
    sys.stdout.buffer.write(body)


def find_footer_processor() -> Path:
    """Locate the PDF footer script in a source checkout or deployment."""
    configured_path = os.environ.get("WATERMARK_ADD_FOOTER")
    if configured_path:
        return Path(configured_path).expanduser().resolve()

    script_path = Path(__file__).resolve()
    home_checkout = Path(os.environ.get("HOME", "/home/anthologizer")) / "acl-anthology"
    for root in (*script_path.parents, home_checkout):
        candidate = root / "bin" / "add_footer_to_pdf.py"
        if candidate.is_file():
            return candidate
    return script_path.parents[2] / "bin" / "add_footer_to_pdf.py"


def parse_content_length() -> int:
    try:
        content_length = int(os.environ.get("CONTENT_LENGTH", ""))
    except ValueError:
        fail(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header.")
    if content_length <= 0:
        fail(HTTPStatus.BAD_REQUEST, "Empty request body.")
    if content_length > MAX_REQUEST_BYTES:
        fail(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            f"Request exceeds the {MAX_PDF_BYTES // 1024 // 1024} MB PDF limit.",
        )
    return content_length


def parse_form(content_length: int):
    content_type = os.environ.get("CONTENT_TYPE", "")
    if "\r" in content_type or "\n" in content_type:
        fail(HTTPStatus.BAD_REQUEST, "Invalid Content-Type header.")

    content_type_header = Message()
    content_type_header["Content-Type"] = content_type
    boundary = content_type_header.get_param("boundary", header="Content-Type")
    if (
        content_type_header.get_content_type() != "multipart/form-data"
        or not boundary
        or len(boundary) > MAX_MULTIPART_BOUNDARY_CHARS
    ):
        fail(
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            "Use multipart/form-data for PDF uploads.",
        )

    request_body = sys.stdin.buffer.read(content_length)
    if len(request_body) != content_length:
        fail(HTTPStatus.BAD_REQUEST, "Incomplete request body.")
    try:
        header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode(
            "ascii"
        )
    except UnicodeEncodeError:
        fail(HTTPStatus.BAD_REQUEST, "Invalid Content-Type header.")

    message = BytesParser(policy=policy.default).parsebytes(header + request_body)
    if message.defects or not message.is_multipart():
        fail(HTTPStatus.BAD_REQUEST, "Invalid multipart request.")
    parts = list(message.iter_parts())
    if not 1 <= len(parts) <= MAX_FORM_PARTS:
        fail(HTTPStatus.BAD_REQUEST, "Invalid number of form fields.")

    form = defaultdict(list)
    files = defaultdict(list)
    for part in parts:
        if part.defects or part.is_multipart():
            fail(HTTPStatus.BAD_REQUEST, "Invalid multipart form field.")
        if part.get_content_disposition() != "form-data":
            fail(HTTPStatus.BAD_REQUEST, "Invalid form field disposition.")
        name = part.get_param("name", header="Content-Disposition")
        if name not in {"pdf", "footer_text", "page_start", *LAYOUT_OPTIONS}:
            fail(HTTPStatus.BAD_REQUEST, "Unexpected form field.")

        payload = part.get_payload(decode=True)
        if payload is None:
            payload = b""
        filename = part.get_filename()
        if filename is not None:
            files[name].append((filename, payload))
            continue

        if len(payload) > MAX_FOOTER_CHARS * 4:
            fail(HTTPStatus.BAD_REQUEST, "Form field is too long.")
        try:
            value = payload.decode(part.get_content_charset() or "utf-8")
        except (LookupError, UnicodeDecodeError):
            fail(HTTPStatus.BAD_REQUEST, "Form field is not valid UTF-8 text.")
        form[name].append(value)

    return form, files


def normalize_footer_text(text: str) -> str:
    text = text.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text).replace("\t", " ")
    if len(text) > MAX_FOOTER_CHARS:
        fail(HTTPStatus.BAD_REQUEST, "Footer text is too long.")
    if len(text.splitlines()) > MAX_FOOTER_LINES:
        fail(HTTPStatus.BAD_REQUEST, "Footer text has too many lines.")
    if any(unicodedata.category(character).startswith("C") for character in text if character != "\n"):
        fail(HTTPStatus.BAD_REQUEST, "Footer text contains unsupported control characters.")

    italic_open = False
    for tag in ITALIC_TAG_RE.findall(text):
        if tag == "<i>":
            if italic_open:
                fail(HTTPStatus.BAD_REQUEST, "Footer text contains nested <i> tags.")
            italic_open = True
        elif not italic_open:
            fail(HTTPStatus.BAD_REQUEST, "Footer text contains an unmatched </i> tag.")
        else:
            italic_open = False
    if italic_open:
        fail(HTTPStatus.BAD_REQUEST, "Footer text contains an unmatched <i> tag.")

    untagged_text = ITALIC_TAG_RE.sub("", text)
    if "<" in untagged_text or ">" in untagged_text:
        fail(HTTPStatus.BAD_REQUEST, "Only <i> and </i> markup is supported.")
    try:
        untagged_text.encode("cp1252")
    except UnicodeEncodeError:
        fail(
            HTTPStatus.BAD_REQUEST,
            "Footer text contains characters unsupported by the PDF font.",
        )
    return text


def parse_page_start(value: str | None) -> int | None:
    if not value:
        return None
    try:
        page_start = int(value)
    except ValueError:
        fail(HTTPStatus.BAD_REQUEST, "Starting page number must be an integer.")
    if not 1 <= page_start <= MAX_PAGE_NUMBER:
        fail(
            HTTPStatus.BAD_REQUEST,
            f"Starting page number must be between 1 and {MAX_PAGE_NUMBER:,}.",
        )
    return page_start


def parse_layout_option(name: str, value: str):
    command_option, label, minimum, maximum = LAYOUT_OPTIONS[name]
    try:
        number = float(value)
    except ValueError:
        fail(HTTPStatus.BAD_REQUEST, f"{label} must be a number.")
    if not math.isfinite(number) or not minimum <= number <= maximum:
        fail(
            HTTPStatus.BAD_REQUEST,
            f"{label} must be between {minimum} and {maximum}.",
        )
    return command_option, f"{number:g}"


def process_request(footer_processor: Path):
    content_length = parse_content_length()
    form, files = parse_form(content_length)
    pdf_parts = files.get("pdf", [])
    if len(pdf_parts) != 1 or not pdf_parts[0][0]:
        fail(HTTPStatus.BAD_REQUEST, "Provide exactly one PDF file.")
    pdf_data = pdf_parts[0][1]
    if len(pdf_data) > MAX_PDF_BYTES:
        fail(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "PDF exceeds the 25 MB limit.")

    footer_values = form.get("footer_text", [])
    page_values = form.get("page_start", [])
    if len(footer_values) > 1 or len(page_values) > 1:
        fail(HTTPStatus.BAD_REQUEST, "Duplicate form fields are not allowed.")
    footer_text = normalize_footer_text(footer_values[0] if footer_values else "")
    page_start = parse_page_start(page_values[0] if page_values else None)
    layout_arguments = []
    for name in LAYOUT_OPTIONS:
        values = form.get(name, [])
        if len(values) > 1:
            fail(HTTPStatus.BAD_REQUEST, "Duplicate form fields are not allowed.")
        if values:
            layout_arguments.extend(parse_layout_option(name, values[0]))
    if not footer_text and page_start is None:
        fail(
            HTTPStatus.BAD_REQUEST,
            "Enter footer text or a starting page number.",
        )

    with tempfile.TemporaryDirectory(prefix="watermark-") as temp_dir:
        input_pdf = Path(temp_dir) / "input.pdf"
        output_pdf = Path(temp_dir) / "output.pdf"
        input_pdf.write_bytes(pdf_data)
        if not pdf_data[:1024].lstrip().startswith(b"%PDF-"):
            fail(HTTPStatus.BAD_REQUEST, "Uploaded file is not a PDF.")

        command = [sys.executable, str(footer_processor)]
        if page_start is not None:
            command.extend(("--page-number", str(page_start)))
        command.extend(layout_arguments)
        command.extend((str(input_pdf), str(output_pdf), footer_text))
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=40,
                check=False,
            )
        except subprocess.TimeoutExpired:
            fail(HTTPStatus.GATEWAY_TIMEOUT, "PDF processing timed out.")

        if result.returncode != 0 or not output_pdf.is_file():
            diagnostic = (result.stderr or result.stdout or "Unknown error").strip()
            print(
                f"watermark.cgi: add_footer_to_pdf.py failed: {diagnostic}",
                file=sys.stderr,
            )
            fail(HTTPStatus.INTERNAL_SERVER_ERROR, "Could not process the PDF.")

        output_size = output_pdf.stat().st_size
        headers = [
            "Content-Type: application/pdf",
            "X-Content-Type-Options: nosniff",
            "Cache-Control: no-store",
            'Content-Disposition: attachment; filename="watermarked.pdf"',
            f"Content-Length: {output_size}",
        ]
        sys.stdout.buffer.write(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
        with output_pdf.open("rb") as output_file:
            shutil.copyfileobj(output_file, sys.stdout.buffer)


def main():
    method = os.environ.get("REQUEST_METHOD", "GET").upper()
    if method != "POST":
        fail(
            HTTPStatus.METHOD_NOT_ALLOWED,
            "Use POST with multipart/form-data.",
            headers=(("Allow", "POST"),),
        )

    footer_processor = find_footer_processor()
    if not footer_processor.is_file():
        print(
            f"watermark.cgi: footer script not found at {footer_processor}",
            file=sys.stderr,
        )
        fail(HTTPStatus.INTERNAL_SERVER_ERROR, "PDF processing is unavailable.")
    process_request(footer_processor)


if __name__ == "__main__":
    try:
        main()
    except RequestError as error:
        write_error(error)
    except BrokenPipeError:
        pass
    except Exception as error:
        print(f"watermark.cgi: unexpected error: {error!r}", file=sys.stderr)
        write_error(
            RequestError(HTTPStatus.INTERNAL_SERVER_ERROR, "Unexpected server error.")
        )
