"""Building and validating chains of blocks. These are pure functions with no I/O.

`validate_block(block, prev, seen)` is the single source of truth for what a
valid block is. Nodes use it before accepting a proposal; `validate_chain`
applies it from genesis to head. Auditors and the tally use that.

Rules checked for every block:
 1. kind is known; genesis exactly at height 0, nothing after a results block
 2. height == prev.height + 1 and election_id matches
 3. prev_hash == prev.block_hash  (genesis: 64 zeros)
 4. block_hash == sha256(header)  (nothing in the header was edited)
 5. block_hash meets the difficulty (proof-of-work was done)
 6. tx_count == len(transactions) > 0 and merkle_root == root(transactions)
 7. every transaction is a sha256 hex digest and appears only once in the
    whole chain (a ballot can't be counted twice)
 8. timestamp is not earlier than the previous block's
 9. genesis and results blocks carry exactly one transaction
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.blockchain.block import BLOCK_KINDS, Block, BlockKind
from app.blockchain.errors import InvalidBlockError
from app.blockchain.hashing import ZERO_HASH, is_hex_hash
from app.blockchain.merkle import merkle_root
from app.blockchain.pow import meets_difficulty, mine


def utc_timestamp() -> str:
    """Current UTC time, rounded to whole seconds, ISO-8601 with 'Z'."""
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_block(
    *,
    election_id: int,
    prev: Block | None,
    kind: BlockKind,
    transactions: list[str],
    difficulty: int,
    sealed_by: str,
    timestamp: str | None = None,
) -> Block:
    """Create and mine the next block on top of `prev` (None → genesis)."""
    if not transactions:
        raise ValueError("a block needs at least one transaction")
    ts = timestamp or utc_timestamp()
    if prev is not None and ts < prev.timestamp:
        ts = prev.timestamp  # clocks can step backwards; never break rule 8
    unmined = Block(
        election_id=election_id,
        height=0 if prev is None else prev.height + 1,
        kind=kind,
        timestamp=ts,
        prev_hash=ZERO_HASH if prev is None else prev.block_hash,
        merkle_root=merkle_root(transactions),
        tx_count=len(transactions),
        nonce=0,
        difficulty=difficulty,
        sealed_by=sealed_by,
        block_hash="",
        transactions=tuple(transactions),
    )
    return mine(unmined)


def validate_block(block: Block, prev: Block | None, seen_txs: set[str] | None = None) -> None:
    """Raise InvalidBlockError if `block` is not a valid successor of `prev`."""
    def fail(reason: str) -> None:
        raise InvalidBlockError(f"block {block.height}: {reason}")

    if block.kind not in BLOCK_KINDS:
        fail(f"unknown kind {block.kind!r}")

    if prev is None:
        if block.height != 0 or block.kind != "genesis":
            fail("first block must be a genesis block at height 0")
        if block.prev_hash != ZERO_HASH:
            fail("genesis prev_hash must be all zeros")
    else:
        if block.kind == "genesis":
            fail("genesis block is only allowed at height 0")
        if prev.kind == "results":
            fail("no blocks may follow the results block")
        if block.height != prev.height + 1:
            fail(f"height should be {prev.height + 1}")
        if block.election_id != prev.election_id:
            fail("election_id does not match the chain")
        if block.prev_hash != prev.block_hash:
            fail("prev_hash does not link to the previous block")
        if block.timestamp < prev.timestamp:
            fail("timestamp is earlier than the previous block")

    if block.computed_hash() != block.block_hash:
        fail("block_hash does not match its contents")
    if not meets_difficulty(block.block_hash, block.difficulty):
        fail("proof-of-work does not meet the difficulty")

    txs = list(block.transactions)
    if block.tx_count != len(txs) or not txs:
        fail("tx_count does not match the transactions")
    if block.kind in ("genesis", "results") and len(txs) != 1:
        fail(f"{block.kind} block must carry exactly one transaction")
    if any(not is_hex_hash(t) for t in txs):
        fail("transactions must be sha256 hex digests")
    if len(set(txs)) != len(txs):
        fail("duplicate transaction inside the block")
    if seen_txs is not None and seen_txs.intersection(txs):
        fail("transaction already recorded in an earlier block")
    if merkle_root(txs) != block.merkle_root:
        fail("merkle_root does not match the transactions")


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of walking a chain from genesis to head."""
    valid: bool
    length: int                      # number of blocks examined
    head_hash: str | None            # hash of the last block (as stored)
    first_bad_height: int | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "length": self.length,
            "head_hash": self.head_hash,
            "first_bad_height": self.first_bad_height,
            "error": self.error,
        }


def validate_chain(blocks: list[Block]) -> ValidationReport:
    """Validate a whole chain. An empty chain is valid (election not started)."""
    head = blocks[-1].block_hash if blocks else None
    seen: set[str] = set()
    prev: Block | None = None
    for index, block in enumerate(blocks):
        if block.height != index:
            return ValidationReport(False, len(blocks), head, index, f"block at position {index} has height {block.height}")
        try:
            validate_block(block, prev, seen)
        except InvalidBlockError as error:
            return ValidationReport(False, len(blocks), head, block.height, str(error))
        seen.update(block.transactions)
        prev = block
    return ValidationReport(True, len(blocks), head)


def ballot_transactions(blocks: list[Block]) -> list[str]:
    """All ballot hashes recorded in `blocks` (skips genesis/results payloads)."""
    return [tx for block in blocks if block.kind == "ballots" for tx in block.transactions]


def find_transaction(blocks: list[Block], tx_hash: str) -> tuple[Block, int] | None:
    """Locate `tx_hash`: returns (block, index within block) or None."""
    for block in blocks:
        if tx_hash in block.transactions:
            return block, block.transactions.index(tx_hash)
    return None
