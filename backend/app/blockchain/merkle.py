"""Merkle tree over a block's transactions (ballot hashes).

A block stores only the Merkle *root*. Anyone holding a receipt can be given
a short *proof* (the sibling hash at each level) and recompute the root
themselves. That shows their ballot is inside the block without
downloading the whole block or trusting the server's "yes, it's there".

Construction (same as Bitcoin, plus domain separation):
* leaf  = sha256(0x00 || tx_hash_bytes)
* node  = sha256(0x01 || left || right)
* odd number of nodes on a level → the last one is paired with itself.

Why the 0x00 / 0x01 prefixes: without them an attacker could present an
internal node as if it were a leaf (second-preimage attack). Prefixing
makes a leaf hash and a node hash impossible to confuse.
"""
import hashlib
from typing import Literal

from app.blockchain.hashing import is_hex_hash

Side = Literal["L", "R"]
ProofStep = tuple[str, Side]  # (sibling hash hex, side the sibling is on)

_LEAF = b"\x00"
_NODE = b"\x01"


def _leaf(tx_hash: str) -> bytes:
    if not is_hex_hash(tx_hash):
        raise ValueError(f"transaction must be a sha256 hex digest: {tx_hash!r}")
    return hashlib.sha256(_LEAF + bytes.fromhex(tx_hash)).digest()


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(_NODE + left + right).digest()


def _next_level(level: list[bytes]) -> list[bytes]:
    if len(level) % 2 == 1:
        level = level + [level[-1]]
    return [_node(level[i], level[i + 1]) for i in range(0, len(level), 2)]


def merkle_root(tx_hashes: list[str]) -> str:
    """Root of the tree over `tx_hashes` (order matters). Raises on an empty list."""
    if not tx_hashes:
        raise ValueError("a Merkle tree needs at least one transaction")
    level = [_leaf(t) for t in tx_hashes]
    while len(level) > 1:
        level = _next_level(level)
    return level[0].hex()


def merkle_proof(tx_hashes: list[str], index: int) -> list[ProofStep]:
    """Inclusion proof for `tx_hashes[index]`: siblings from leaf to root."""
    if not 0 <= index < len(tx_hashes):
        raise IndexError("transaction index out of range")
    level = [_leaf(t) for t in tx_hashes]
    proof: list[ProofStep] = []
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = level + [level[-1]]
        if index % 2 == 0:
            proof.append((level[index + 1].hex(), "R"))
        else:
            proof.append((level[index - 1].hex(), "L"))
        level = [_node(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        index //= 2
    return proof


def verify_proof(tx_hash: str, proof: list[ProofStep] | list[list[str]], root: str) -> bool:
    """Recompute the root from `tx_hash` + `proof` and compare with `root`."""
    try:
        current = _leaf(tx_hash)
        for sibling_hex, side in proof:
            sibling = bytes.fromhex(sibling_hex)
            current = _node(sibling, current) if side == "L" else _node(current, sibling)
    except (ValueError, TypeError):
        return False
    return current.hex() == root
