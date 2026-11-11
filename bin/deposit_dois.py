#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Matt Post <post@cs.jhu.edu>
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

"""Generates Crossref DOI metadata and deposits it directly with Crossref.

Accepts the same volume and event IDs as generate_crossref_doi_metadata.py:

    uv run bin/deposit_dois.py 2024.emnlp-main 2024.emnlp-long
    uv run bin/deposit_dois.py emnlp-2024 --wait
    uv run bin/deposit_dois.py W10-17 --dry-run

Each DOI registered costs the ACL $1 USD; see the policy notes in
generate_crossref_doi_metadata.py before depositing.

Authentication uses Crossref account credentials, read from the environment:

    CROSSREF_USERNAME  role name (shared role credentials), or
                       email@address/role (personal user credentials)
    CROSSREF_PASSWORD  the corresponding password

Missing values are prompted for interactively; the password is never accepted
as a command-line argument.

Deposits are processed asynchronously by Crossref; use --wait to poll for the
processing result. This script does not add DOIs to the Anthology XML; for
that, run bin/add_dois.py afterwards.
"""

import argparse
import getpass
import logging
import os
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from lxml import etree

from acl_anthology import Anthology
from acl_anthology.utils.logging import setup_rich_logging

from generate_crossref_doi_metadata import (
    MAX_FILE_BYTES,
    generate_crossref_xml,
    resolve_inputs,
    split_volume_ids_by_size,
)

log = logging.getLogger(__name__)

PRODUCTION_HOST = "https://doi.crossref.org"
TEST_HOST = "https://test.crossref.org"
CROSSREF_NS = "{http://www.crossref.org/schema/4.4.1}"
PENDING_STATUSES = {"queued", "in_process", "unknown_submission"}


class DepositError(Exception):
    pass


def get_credentials():
    username = os.environ.get("CROSSREF_USERNAME") or input("Crossref username: ")
    password = os.environ.get("CROSSREF_PASSWORD") or getpass.getpass(
        "Crossref password: "
    )
    if not username or not password:
        raise DepositError("Crossref username and password are required")
    return username, password


def count_dois(xml_bytes):
    root = etree.fromstring(xml_bytes)
    return len(root.findall(f".//{CROSSREF_NS}doi"))


def encode_multipart(fields, file_field, filename, content):
    """Encode form fields plus one XML file as multipart/form-data."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode("utf-8")
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; "
        f'name="{file_field}"; filename="{filename}"\r\n'
        "Content-Type: application/xml\r\n\r\n".encode("utf-8")
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def deposit(host, username, password, filename, xml_bytes):
    """POST one metadata file to Crossref's deposit queue."""
    body, content_type = encode_multipart(
        {
            "operation": "doMDUpload",
            "login_id": username,
            "login_passwd": password,
        },
        "fname",
        filename,
        xml_bytes,
    )
    request = Request(
        f"{host}/servlet/deposit",
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urlopen(request, timeout=300) as response:
            text = response.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise DepositError(f"Crossref rejected {filename}: HTTP {e.code}: {detail}")
    except URLError as e:
        raise DepositError(f"Could not reach Crossref: {e.reason}")
    if "SUCCESS" not in text:
        raise DepositError(f"Unexpected Crossref response for {filename}: {text}")


def fetch_result(host, username, password, filename):
    """Retrieve the processing result for a deposit, tracked by file name."""
    params = urlencode(
        {
            "usr": username,
            "pwd": password,
            "file_name": filename,
            "type": "result",
        }
    )
    try:
        with urlopen(f"{host}/servlet/submissionDownload?{params}", timeout=60) as r:
            return r.read()
    except HTTPError as e:
        raise DepositError(f"Could not retrieve result for {filename}: HTTP {e.code}")
    except URLError as e:
        raise DepositError(f"Could not reach Crossref: {e.reason}")


def parse_result(result_bytes):
    """Return (status, counts) from a Crossref doi_batch_diagnostic report."""
    try:
        root = etree.fromstring(result_bytes)
    except etree.XMLSyntaxError:
        return "unknown_submission", {}
    counts = {}
    batch_data = root.find("batch_data")
    if batch_data is not None:
        for child in batch_data:
            if child.text and child.text.strip().isdigit():
                counts[child.tag] = int(child.text)
    return root.get("status", "unknown_submission"), counts


def wait_for_result(host, username, password, filename, timeout, interval):
    deadline = time.monotonic() + timeout
    while True:
        status, counts = parse_result(fetch_result(host, username, password, filename))
        if status not in PENDING_STATUSES:
            return status, counts
        if time.monotonic() >= deadline:
            return status, counts
        log.info("%s is %s; checking again in %ds", filename, status, interval)
        time.sleep(interval)


def confirm(message):
    try:
        return input(f"{message} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def main(args):
    setup_rich_logging()
    anthology = Anthology.from_within_repo(verbose=False)
    volume_ids = resolve_inputs(anthology, args.identifiers)
    for volume_id in volume_ids:
        if anthology.get_volume(volume_id) is None:
            raise DepositError(f"Volume {volume_id} not found")

    chunks = split_volume_ids_by_size(anthology, volume_ids, MAX_FILE_BYTES)
    base_batch_id = int(time.time())
    batches = []
    for i, chunk in enumerate(chunks):
        batch_id = base_batch_id + i
        xml_bytes = generate_crossref_xml(anthology, chunk, batch_id=batch_id)
        batches.append((f"anthology_{batch_id}.xml", chunk, xml_bytes))

    total_dois = sum(count_dois(xml_bytes) for _, _, xml_bytes in batches)
    host = TEST_HOST if args.test else PRODUCTION_HOST
    for filename, chunk, xml_bytes in batches:
        log.info(
            "%s: %d volumes, %d DOIs, %d bytes",
            filename,
            len(chunk),
            count_dois(xml_bytes),
            len(xml_bytes),
        )

    if args.dry_run:
        log.info("Dry run: would deposit %d DOIs to %s", total_dois, host)
        return

    if not args.test and not args.yes:
        if not confirm(f"Register {total_dois} DOIs with Crossref (production)?"):
            log.info("Aborted; nothing was deposited")
            return

    username, password = get_credentials()

    for filename, _, xml_bytes in batches:
        deposit(host, username, password, filename, xml_bytes)
        log.info("Submitted %s to %s", filename, host)

    if not args.wait:
        log.info(
            "Crossref processes deposits asynchronously; results will be emailed. "
            "Rerun with --wait to poll for them."
        )
        return

    failed = False
    for filename, _, _ in batches:
        status, counts = wait_for_result(
            host, username, password, filename, args.timeout, args.poll_interval
        )
        log.info("%s: %s %s", filename, status, counts)
        if status != "completed" or counts.get("failure_count", 0) > 0:
            failed = True
    if failed:
        raise DepositError(
            "Some deposits did not complete successfully; check the Crossref logs"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Crossref DOI metadata and deposit it with Crossref."
    )
    parser.add_argument(
        "identifiers",
        nargs="+",
        help="Volume IDs (e.g., 2024.emnlp-main, W10-17) or event IDs (e.g., emnlp-2024)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and summarize the deposits without submitting them",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help=f"Deposit to the Crossref test system ({TEST_HOST})",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt for production deposits",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll Crossref until each deposit has been processed",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Maximum seconds to wait per deposit with --wait (default: 1800)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between status checks with --wait (default: 30)",
    )
    try:
        main(parser.parse_args())
    except DepositError as e:
        log.error("%s", e)
        sys.exit(1)
