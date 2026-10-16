"""Hashing helpers shared by every blockchain module.

`canonical_json` is THE single definition of how a structure becomes bytes
before hashing: sorted keys, no whitespace, UTF-8. If two pieces of code
serialised differently, the same block would get two different hashes, so
everything goes through here.
"""
import hashlib
import json
from typing import Any

ZERO_HASH = "0" * 64  # prev_hash of every genesis block


def canonical_json(data: Any) -> bytes:
    """Deterministic JSON encoding used for all hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes | str) -> str:
    """SHA-256 of bytes (or a UTF-8 string) as 64 lowercase hex characters."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def hash_object(data: Any) -> str:
    """SHA-256 of the canonical JSON of `data`."""
    return sha256_hex(canonical_json(data))


def is_hex_hash(value: object) -> bool:
    """True if `value` looks like a SHA-256 hex digest."""
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
