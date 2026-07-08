#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys

from patch_signer import deserialize_signature, load_bytes, load_ed25519_public, load_hmac_key, verify_hmac, verify_ed25519


def main() -> int:
    parser = argparse.ArgumentParser(description="CLI wrapper for patch signature verification.")
    parser.add_argument("--method", choices=["hmac", "ed25519"], required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--patch", required=True)
    parser.add_argument("--signature", required=True)
    args = parser.parse_args()

    patch_bytes = load_bytes(Path(args.patch))
    signature_blob = json.loads(Path(args.signature).read_text(encoding="utf-8"))
    method = signature_blob["method"]
    signature = deserialize_signature(signature_blob["signature"])

    if method != args.method:
        print(f"Mismatch: signature method is {method}, but CLI method is {args.method}")
        return 1

    if method == "hmac":
        key = load_hmac_key(Path(args.key))
        valid = verify_hmac(key, patch_bytes, signature)
    else:
        public_key = load_ed25519_public(Path(args.key))
        valid = verify_ed25519(public_key, patch_bytes, signature)

    if valid:
        print("Verification succeeded.")
        return 0

    print("Verification failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
