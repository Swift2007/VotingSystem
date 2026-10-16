"""Receipt codes.

A receipt code looks like ``VC-7QK4-93X2-2H8P``: the prefix "VC" plus 12
characters from a 32-symbol alphabet without look-alikes (no 0/O, 1/I),
giving 60 bits of randomness. That matches the format the frontend expects
(`Frontend/js/pages/verify-receipt.js`).

The server stores only sha256(normalised code) in `receipts`, next to the
ballot hash, with NO user column. The code is shown to the student once and
never again (decision D-005). The student keeps it (the frontend may save it
in the browser); the server can't look it up for them.
"""
import secrets

from app.blockchain.hashing import sha256_hex

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PREFIX = "VC"
BODY_LENGTH = 12


def new_receipt_code() -> str:
    """A fresh, human-friendly code, e.g. 'VC-7QK4-93X2-2H8P'."""
    body = "".join(secrets.choice(ALPHABET) for _ in range(BODY_LENGTH))
    return f"{PREFIX}-{body[0:4]}-{body[4:8]}-{body[8:12]}"


def normalize_receipt_code(code: str) -> str:
    """Uppercase and strip spaces, dots, dashes: 'vc · 7qk4-…' → 'VC7QK4…'."""
    return "".join(ch for ch in code.upper() if ch.isalnum())


def is_well_formed(code: str) -> bool:
    norm = normalize_receipt_code(code)
    return (
        len(norm) == len(PREFIX) + BODY_LENGTH
        and norm.startswith(PREFIX)
        and all(ch in ALPHABET for ch in norm[len(PREFIX):])
    )


def receipt_hash(code: str) -> str:
    """What the database stores for a receipt."""
    return sha256_hex("receipt:" + normalize_receipt_code(code))
