"""The Block data structure and the rule for computing its hash.

A block has a *header* (everything below except `transactions` and
`block_hash`) and a body (`transactions`). The header contains the Merkle root
of the body, so hashing the header commits to every transaction:

    block_hash = sha256(canonical_json(header))

Changing a single character of any transaction changes the merkle root,
which changes the block hash, which breaks the `prev_hash` link of the next
block. That is the "tamper-evident" property.

Block kinds
-----------
* ``genesis``  height 0. One transaction: the hash of the election's public
               parameters (title, voting window, candidates, key fingerprint).
               This anchors the election setup so later edits are detectable.
* ``ballots``  one or more ballot hashes, in shuffled order.
* ``results``  last block. One transaction: the hash of the published results.
"""
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal

from app.blockchain.hashing import hash_object

BlockKind = Literal["genesis", "ballots", "results"]
BLOCK_KINDS: tuple[str, ...] = ("genesis", "ballots", "results")

# Fields that go into the hash, in documentation order (hashing sorts keys anyway).
HEADER_FIELDS = (
    "election_id", "height", "kind", "timestamp", "prev_hash",
    "merkle_root", "tx_count", "nonce", "difficulty", "sealed_by",
)


@dataclass(frozen=True)
class Block:
    election_id: int
    height: int
    kind: BlockKind
    timestamp: str          # UTC ISO-8601, whole seconds (no finer timing leaks)
    prev_hash: str
    merkle_root: str
    tx_count: int
    nonce: int
    difficulty: int         # number of leading hex zeros the hash must have
    sealed_by: str          # id of the simulated node that proposed it
    block_hash: str
    transactions: tuple[str, ...] = field(default_factory=tuple)

    def header(self) -> dict[str, Any]:
        """The hashed part of the block."""
        return {name: getattr(self, name) for name in HEADER_FIELDS}

    def computed_hash(self) -> str:
        """Recompute the hash from the header (ignores the stored block_hash)."""
        return compute_block_hash(self.header())

    def with_nonce(self, nonce: int) -> "Block":
        """Copy with a new nonce and a freshly computed hash (used by mining)."""
        updated = replace(self, nonce=nonce, block_hash="")
        return replace(updated, block_hash=updated.computed_hash())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["transactions"] = list(self.transactions)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Block":
        values = {name: data[name] for name in HEADER_FIELDS}
        return cls(
            **values,
            block_hash=data["block_hash"],
            transactions=tuple(data.get("transactions", ())),
        )


def compute_block_hash(header: dict[str, Any]) -> str:
    """sha256 over the canonical JSON of exactly the header fields."""
    return hash_object({name: header[name] for name in HEADER_FIELDS})
