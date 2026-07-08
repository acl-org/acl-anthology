#!/usr/bin/env python3

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


def load_bytes(path: Path) -> bytes:
    return path.read_bytes()


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def generate_hmac_key(path: Path) -> None:
    key = os.urandom(32)
    path.write_bytes(key)
    print(f"Generated HMAC key at {path}")


def generate_ed25519_key(path: Path) -> None:
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package is required for Ed25519 key generation")

    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    path.write_bytes(pem)
    print(f"Generated Ed25519 private key at {path}")


def load_hmac_key(path: Path) -> bytes:
    return path.read_bytes()


def load_ed25519_private(path: Path) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def load_ed25519_public(path: Path) -> Ed25519PublicKey:
    return serialization.load_pem_public_key(path.read_bytes())


def sign_hmac(key: bytes, payload: bytes) -> bytes:
    return hmac.new(key, payload, hashlib.sha256).digest()


def verify_hmac(key: bytes, payload: bytes, signature: bytes) -> bool:
    expected = sign_hmac(key, payload)
    return hmac.compare_digest(expected, signature)


def sign_ed25519(private_key: Ed25519PrivateKey, payload: bytes) -> bytes:
    return private_key.sign(payload)


def verify_ed25519(public_key: Ed25519PublicKey, payload: bytes, signature: bytes) -> bool:
    try:
        public_key.verify(signature, payload)
        return True
    except Exception:
        return False


def serialize_signature(signature: bytes) -> str:
    return base64.b64encode(signature).decode("utf-8")


def deserialize_signature(signature_text: str) -> bytes:
    return base64.b64decode(signature_text.encode("utf-8"))


def make_signature_blob(method: str, signature: bytes) -> str:
    payload = {
        "method": method,
        "signature": serialize_signature(signature),
    }
    return json.dumps(payload, indent=2)


def sign_patch(args: argparse.Namespace) -> int:
    patch_bytes = load_bytes(Path(args.patch))
    method = args.method or ("ed25519" if CRYPTO_AVAILABLE else "hmac")

    if method == "hmac":
        key = load_hmac_key(Path(args.key))
        signature = sign_hmac(key, patch_bytes)
    elif method == "ed25519":
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Ed25519 signing requires the cryptography package.")
        private_key = load_ed25519_private(Path(args.key))
        signature = sign_ed25519(private_key, patch_bytes)
    else:
        raise ValueError(f"Unsupported signing method: {method}")

    blob = make_signature_blob(method, signature)
    if args.signature:
        write_text(Path(args.signature), blob)
        print(f"Wrote signature file: {args.signature}")
    else:
        print(blob)
    return 0


def verify_patch(args: argparse.Namespace) -> int:
    patch_bytes = load_bytes(Path(args.patch))
    blob = json.loads(Path(args.signature).read_text(encoding="utf-8"))
    method = blob["method"]
    signature = deserialize_signature(blob["signature"])

    if method == "hmac":
        key = load_hmac_key(Path(args.key))
        ok = verify_hmac(key, patch_bytes, signature)
    elif method == "ed25519":
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Ed25519 verification requires the cryptography package.")
        public_key = load_ed25519_public(Path(args.key))
        ok = verify_ed25519(public_key, patch_bytes, signature)
    else:
        raise ValueError(f"Unsupported signature method: {method}")

    if ok:
        print("Signature verification passed.")
        return 0

    print("Signature verification failed.")
    return 1


def generate_key(args: argparse.Namespace) -> int:
    path = Path(args.output)
    if args.type == "hmac":
        generate_hmac_key(path)
    elif args.type == "ed25519":
        generate_ed25519_key(path)
    else:
        raise ValueError(f"Unsupported key type: {args.type}")
    return 0


def export_public_key(args: argparse.Namespace) -> int:
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package is required to export public keys.")
    private_key = load_ed25519_private(Path(args.private_key))
    public_key = private_key.public_key()
    pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    Path(args.output).write_bytes(pem)
    print(f"Exported public key to {args.output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign and verify patch files for secure correction workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate-key", help="Generate a signing key.")
    gen.add_argument("--type", choices=["hmac", "ed25519"], default="hmac")
    gen.add_argument("--output", required=True)
    gen.set_defaults(func=generate_key)

    export = subparsers.add_parser("export-public", help="Export a public key from an Ed25519 private key.")
    export.add_argument("--private-key", required=True)
    export.add_argument("--output", required=True)
    export.set_defaults(func=export_public_key)

    sign = subparsers.add_parser("sign", help="Sign a patch file.")
    sign.add_argument("--method", choices=["hmac", "ed25519"], help="Signing method to use.")
    sign.add_argument("--key", required=True)
    sign.add_argument("--patch", required=True)
    sign.add_argument("--signature", help="Output signature file path. Writes to stdout if omitted.")
    sign.set_defaults(func=sign_patch)

    verify = subparsers.add_parser("verify", help="Verify a patch signature.")
    verify.add_argument("--key", required=True, help="Public key for Ed25519 or secret key for HMAC.")
    verify.add_argument("--patch", required=True)
    verify.add_argument("--signature", required=True)
    verify.set_defaults(func=verify_patch)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
