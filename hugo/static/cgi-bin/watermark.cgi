#!/opt/venv/watermark/bin/python3
# -*- coding: utf-8 -*-
"""
watermark.cgi - On-the-fly PDF footer + page number service for the ACL Anthology.

POST a multipart/form-data request with fields:
  pdf          (file, required)  The input PDF
  footer_text  (text, optional)  First-page footer block; use <i>…</i> for italics; newlines allowed
  page_start   (int, optional)   Starting page number (>=1)

Returns: Modified PDF (application/pdf) with Content-Disposition: attachment.

Security / Resource considerations:
  * Rejects files > 30MB (quick limit; adjust as needed).
  * Basic PDF validation (magic header %PDF-).
  * Uses temporary files; they are deleted at end of request.
  * No persistent storage.

Depends on: reportlab, pypdf (already required by bin/add_footer.py)
"""

import cgi
import os
import sys
import tempfile
import subprocess
from pathlib import Path
import shutil
import urllib.parse
MAX_BYTES = 30 * 1024 * 1024

def http_error(status_code: int, message: str):
    print(f"Status: {status_code} Bad Request" if status_code == 400 else f"Status: {status_code}")
    print("Content-Type: text/plain; charset=utf-8")
    print("X-Content-Type-Options: nosniff")
    print()
    print(message)
    sys.exit(0)

def find_add_footer() -> Path:
    """Resolve location of add_footer.py relative to this CGI script."""
    here = Path(__file__).resolve()
    homedir = Path(os.environ.get('HOME', '/home/anthologizer'))
    # Walk up to locate bin/add_footer.py
    for parent in [here.parent, *here.parents, homedir / "acl-anthology"]:
        candidate = parent.parent / "bin" / "add_footer.py" if parent.name == 'cgi-bin' else parent / "bin" / "add_footer.py"
        if candidate.exists():
            return candidate
    # Fallback relative guess (3 levels up)
    guess = here.parents[2] / 'bin' / 'add_footer.py'
    return guess

def main():
    # Debug flag: append ?debug=1 to request URL to get full stderr on failure.
    qs = os.environ.get('QUERY_STRING', '')
    qparams = dict(urllib.parse.parse_qsl(qs, keep_blank_values=True)) if qs else {}
    debug_mode = qparams.get('debug') in {'1','true','yes','on'}
    method = os.environ.get('REQUEST_METHOD', 'GET').upper()
    if method != 'POST':
        http_error(405, 'Use POST with multipart/form-data.')

    try:
        length = int(os.environ.get('CONTENT_LENGTH', '0'))
    except ValueError:
        length = 0
    if length <= 0:
        http_error(400, 'Empty request body.')
    if length > MAX_BYTES:
        http_error(400, f'File too large (> {MAX_BYTES//1024//1024}MB).')

    form = cgi.FieldStorage()

    if 'pdf' not in form or not getattr(form['pdf'], 'file', None):
        http_error(400, 'Missing PDF file.')
    pdf_item = form['pdf']
    footer_text = form.getfirst('footer_text', '')[:10000]  # cap length
    page_start_raw = form.getfirst('page_start')
    page_start = None
    if page_start_raw:
        try:
            page_start = int(page_start_raw)
            if page_start < 1:
                raise ValueError
        except ValueError:
            http_error(400, 'Invalid page_start (must be positive integer).')

    # Write uploaded PDF to temp file
    tmp_dir = tempfile.mkdtemp(prefix='wmk_')
    input_pdf = Path(tmp_dir) / 'input.pdf'
    output_pdf = Path(tmp_dir) / 'output.pdf'

    with open(input_pdf, 'wb') as f:
        # stream copy to avoid loading entire file in memory
        chunked = 0
        while True:
            buf = pdf_item.file.read(64 * 1024)
            if not buf:
                break
            chunked += len(buf)
            if chunked > MAX_BYTES:
                f.close()
                http_error(400, 'File exceeded size limit during upload.')
            f.write(buf)

    # Validate PDF magic
    try:
        with open(input_pdf, 'rb') as f:
            head = f.read(8)
            if b'%PDF-' not in head:
                http_error(400, 'Uploaded file is not a PDF.')
    except Exception:
        http_error(400, 'Could not read uploaded PDF.')

    add_footer = find_add_footer()
    if not add_footer.exists():
        http_error(500, 'Server configuration error: add_footer.py not found.')

    cmd = [sys.executable, str(add_footer)]
    if page_start is not None:
        cmd += ['-p', str(page_start)]
    # Convert embedded newlines are preserved; add_footer.py will handle them
    cmd += [str(input_pdf), str(output_pdf), footer_text]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        http_error(500, 'Processing timed out.')

    if proc.returncode != 0 or not output_pdf.exists():
        stderr = (proc.stderr or '').strip()
        stdout = (proc.stdout or '').strip()
        if debug_mode:
            # Return full diagnostic (no truncation) for troubleshooting.
            diag = [
                'Status: processing failed',
                'Command: ' + ' '.join(cmd),
                f'Return code: {proc.returncode}',
                '--- STDERR ---', stderr or '<empty>',
                '--- STDOUT ---', stdout or '<empty>'
            ]
            http_error(500, '\n'.join(diag))
        else:
            merged = stderr or stdout or 'Unknown error'
            http_error(500, f'Failed to process PDF. (Add ?debug=1 for details)\n{merged[:400]}')

    # Success: stream file
    size = output_pdf.stat().st_size
    # Some Apache configurations are picky about the "Status" header in CGI output.
    # Emit only standard headers followed by a blank line, then raw PDF bytes.
    sys.stdout.write('Content-Type: application/pdf\r\n')
    sys.stdout.write('X-Content-Type-Options: nosniff\r\n')
    sys.stdout.write(f'Content-Disposition: attachment; filename="watermarked.pdf"\r\n')
    sys.stdout.write(f'Content-Length: {size}\r\n')
    sys.stdout.write('\r\n')
    sys.stdout.flush()
    with open(output_pdf, 'rb') as f:
        shutil.copyfileobj(f, sys.stdout.buffer)

    # Cleanup temp dir
    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

if __name__ == '__main__':
    main()
