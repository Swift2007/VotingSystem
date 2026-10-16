"""Toy proof-of-work.

A block is only valid if its hash starts with `difficulty` hex zeros. The
proposer finds such a hash by trying nonce = 0, 1, 2, ... ("mining").

Why have it in a simulation? It makes the tamper-evidence tangible: to
quietly change block 3, an attacker must re-mine block 3 *and every block
after it*, and also convince the majority of nodes. Each extra zero makes
mining ~16x slower; the default difficulty of 3 takes milliseconds.
This is NOT a security guarantee here. All nodes run on one machine.
"""
from app.blockchain.block import Block


def meets_difficulty(block_hash: str, difficulty: int) -> bool:
    """True if `block_hash` has at least `difficulty` leading hex zeros."""
    return block_hash.startswith("0" * difficulty)


def mine(block: Block, max_attempts: int = 50_000_000) -> Block:
    """Return a copy of `block` with a nonce whose hash meets its difficulty."""
    for nonce in range(max_attempts):
        candidate = block.with_nonce(nonce)
        if meets_difficulty(candidate.block_hash, block.difficulty):
            return candidate
    raise RuntimeError("proof-of-work not found; lower POW_DIFFICULTY")
