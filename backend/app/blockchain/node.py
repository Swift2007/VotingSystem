"""One simulated validator node.

Each node keeps its OWN copy of every election's chain in an append-only
JSON-lines file:

    <CHAIN_DATA_DIR>/<node_id>/election_<id>.jsonl   (one block per line)

Keeping separate copies is what makes the simulation meaningful. If someone
edits one node's file (or the database), the other nodes still hold the
original, and `SimNetwork.audit()` spots the difference.

A node never trusts a proposal: `check()` runs the full `validate_block`
rules against the node's own chain head before it agrees to append.
"""
import json
import os
import secrets
import tempfile
from dataclasses import replace
from pathlib import Path

from app.blockchain.block import Block
from app.blockchain.chain import ValidationReport, validate_block, validate_chain
from app.blockchain.errors import InvalidBlockError
from app.blockchain.merkle import merkle_root
from app.blockchain.pow import mine


class SimNode:
    def __init__(self, node_id: str, root_dir: str | Path) -> None:
        self.node_id = node_id
        self.dir = Path(root_dir) / node_id
        self.dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ storage
    def path(self, election_id: int) -> Path:
        return self.dir / f"election_{election_id}.jsonl"

    def load(self, election_id: int) -> tuple[list[Block], str | None]:
        """Read the chain from disk. Returns (blocks, parse_error).

        Always reads the file, so edits made outside the app are seen.
        A line that can't be parsed stops loading and is reported.
        """
        path = self.path(election_id)
        if not path.exists():
            return [], None
        blocks: list[Block] = []
        with path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh):
                if not line.strip():
                    continue
                try:
                    blocks.append(Block.from_dict(json.loads(line)))
                except (ValueError, KeyError, TypeError) as error:
                    return blocks, f"line {line_no + 1} unreadable: {error}"
        return blocks, None

    def chain(self, election_id: int) -> list[Block]:
        return self.load(election_id)[0]

    def head(self, election_id: int) -> Block | None:
        blocks = self.chain(election_id)
        return blocks[-1] if blocks else None

    def _append(self, block: Block) -> None:
        with self.path(block.election_id).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(block.to_dict(), sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def _rewrite(self, election_id: int, blocks: list[Block]) -> None:
        """Atomically replace the file (used only by resync and the tamper demo)."""
        fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for block in blocks:
                fh.write(json.dumps(block.to_dict(), sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path(election_id))

    # ---------------------------------------------------------------- consensus
    def check(self, block: Block) -> str | None:
        """Validate a proposal against this node's chain. Returns a reason or None."""
        blocks, parse_error = self.load(block.election_id)
        if parse_error:
            return f"local chain unreadable ({parse_error})"
        # A node whose own history is corrupt must not vote. It would be
        # extending a chain it can't vouch for. (O(n) per proposal; fine at this scale.)
        own = validate_chain(blocks)
        if not own.valid:
            return f"local chain invalid ({own.error})"
        prev = blocks[-1] if blocks else None
        seen = {tx for b in blocks for tx in b.transactions}
        try:
            validate_block(block, prev, seen)
        except InvalidBlockError as error:
            return str(error)
        return None

    def append(self, block: Block) -> None:
        """Persist an accepted block (only after `check` passed and consensus was reached)."""
        self._append(block)

    def validate(self, election_id: int) -> ValidationReport:
        blocks, parse_error = self.load(election_id)
        report = validate_chain(blocks)
        if parse_error and report.valid:
            return ValidationReport(False, len(blocks), report.head_hash, len(blocks), parse_error)
        return report

    def replace_chain(self, election_id: int, blocks: list[Block]) -> None:
        self._rewrite(election_id, blocks)

    def election_ids(self) -> list[int]:
        ids = []
        for path in self.dir.glob("election_*.jsonl"):
            try:
                ids.append(int(path.stem.split("_", 1)[1]))
            except ValueError:
                continue
        return sorted(ids)

    # ------------------------------------------------------ tamper demo (dev only)
    def tamper(self, election_id: int, height: int, mode: str) -> str:
        """Corrupt this node's copy to show detection. Returns a description.

        Modes:
        * ``edit``   swap one transaction for a random hash, touching nothing else.
                     The merkle root no longer matches, so this node's own
                     validation fails at `height`.
        * ``remine`` swap a transaction, then recompute the merkle root and
                     re-mine this block and every later one. The node's chain is
                     internally valid again, but its head differs from the
                     majority, so the network audit catches it.
        * ``drop``   delete the last block. The node falls behind (out of sync).
        """
        blocks = self.chain(election_id)
        if not blocks:
            raise ValueError("this node has no chain for that election")
        if mode == "drop":
            self._rewrite(election_id, blocks[:-1])
            return f"{self.node_id}: dropped block {blocks[-1].height}"
        if not 0 <= height < len(blocks):
            raise ValueError("height out of range")

        target = blocks[height]
        fake_tx = secrets.token_hex(32)
        txs = (fake_tx,) + target.transactions[1:]
        if mode == "edit":
            blocks[height] = replace(target, transactions=txs)
            self._rewrite(election_id, blocks)
            return f"{self.node_id}: edited a transaction in block {height} without re-mining"
        if mode == "remine":
            prev_hash = target.prev_hash
            for h in range(height, len(blocks)):
                b = blocks[h]
                if h == height:
                    b = replace(b, transactions=txs, merkle_root=merkle_root(list(txs)))
                b = mine(replace(b, prev_hash=prev_hash))
                blocks[h] = b
                prev_hash = b.block_hash
            self._rewrite(election_id, blocks)
            return f"{self.node_id}: rewrote block {height} and re-mined {len(blocks) - height} block(s)"
        raise ValueError(f"unknown tamper mode {mode!r}")
