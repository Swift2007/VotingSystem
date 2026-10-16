"""ChainService: the only entry point the rest of the app uses for the chain.

It glues the pure blockchain modules to the database:

    voting service ──submit()──► mempool ──seal()──► build+mine block
                                                 └─► network.propose()  (majority)
                                                 └─► DB read copy (chain_blocks, block_transactions)

Sealing is serialised by a process-wide lock, so only one block is built at a
time and heights never collide. Mining runs *outside* any database
transaction so it never holds the SQLite write lock.

Source of truth: the network's majority chain. The database tables are an
indexed copy for fast lookups. `verify()` compares the two and reports any
mismatch. Nothing ever "repairs" history from the database (README §4 Backups).
"""
import logging
import secrets
import threading
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blockchain.block import Block, BlockKind
from app.blockchain.chain import build_block, validate_chain
from app.blockchain.errors import ChainFinalizedError, ChainIntegrityError, ConsensusError
from app.blockchain.mempool import Mempool
from app.blockchain.merkle import merkle_proof
from app.blockchain.network import SimNetwork
from app.models import Ballot, BlockTransaction, ChainBlock

log = logging.getLogger("app.blockchain")


class ChainService:
    def __init__(
        self,
        *,
        data_dir: str,
        node_count: int,
        difficulty: int,
        block_size: int,
        block_interval_seconds: float,
    ) -> None:
        self.network = SimNetwork(data_dir, node_count)
        self.mempool = Mempool()
        self.difficulty = difficulty
        self.block_size = block_size
        self.block_interval_seconds = block_interval_seconds
        self._lock = threading.RLock()
        self._rng = secrets.SystemRandom()  # CSPRNG for shuffling ballot order

    # ================================================================ DB copy
    @staticmethod
    def _row_to_block(row: ChainBlock, txs: list[str]) -> Block:
        return Block(
            election_id=row.election_id, height=row.height, kind=row.kind,  # type: ignore[arg-type]
            timestamp=row.timestamp, prev_hash=row.prev_hash, merkle_root=row.merkle_root,
            tx_count=row.tx_count, nonce=row.nonce, difficulty=row.difficulty,
            sealed_by=row.sealed_by, block_hash=row.block_hash, transactions=tuple(txs),
        )

    def _block_txs(self, db: Session, election_id: int, height: int) -> list[str]:
        return list(db.scalars(
            select(BlockTransaction.tx_hash)
            .where(BlockTransaction.election_id == election_id, BlockTransaction.height == height)
            .order_by(BlockTransaction.position)
        ))

    def db_chain(self, db: Session, election_id: int) -> list[Block]:
        """The database read copy of an election's chain, genesis first."""
        rows = db.scalars(
            select(ChainBlock).where(ChainBlock.election_id == election_id).order_by(ChainBlock.height)
        ).all()
        txs: dict[int, list[str]] = {}
        for t in db.scalars(
            select(BlockTransaction).where(BlockTransaction.election_id == election_id)
            .order_by(BlockTransaction.height, BlockTransaction.position)
        ):
            txs.setdefault(t.height, []).append(t.tx_hash)
        return [self._row_to_block(r, txs.get(r.height, [])) for r in rows]

    def db_head(self, db: Session, election_id: int) -> Block | None:
        row = db.scalars(
            select(ChainBlock).where(ChainBlock.election_id == election_id)
            .order_by(ChainBlock.height.desc()).limit(1)
        ).first()
        return None if row is None else self._row_to_block(row, self._block_txs(db, election_id, row.height))

    @staticmethod
    def _store(db: Session, block: Block) -> None:
        db.add(ChainBlock(
            election_id=block.election_id, height=block.height, kind=block.kind,
            timestamp=block.timestamp, prev_hash=block.prev_hash, merkle_root=block.merkle_root,
            tx_count=block.tx_count, nonce=block.nonce, difficulty=block.difficulty,
            sealed_by=block.sealed_by, block_hash=block.block_hash,
        ))
        for position, tx in enumerate(block.transactions):
            db.add(BlockTransaction(
                election_id=block.election_id, height=block.height, position=position, tx_hash=tx,
            ))

    # ================================================================ writing
    def _commit_block(self, db: Session, election_id: int, kind: BlockKind, txs: list[str]) -> Block:
        """Build, mine, reach consensus on, and store one block. Caller holds the lock."""
        prev = self.db_head(db, election_id)
        db.rollback()  # release the SQLite write lock while mining
        if prev is not None and prev.kind == "results":
            raise ChainFinalizedError(f"election {election_id} chain is finalised")

        height = 0 if prev is None else prev.height + 1
        block = build_block(
            election_id=election_id, prev=prev, kind=kind, transactions=txs,
            difficulty=self.difficulty, sealed_by=self.network.proposer_for(height).node_id,
        )
        result = self.network.propose(block)  # raises ConsensusError if no majority
        if result.rejected_by:
            log.warning("election %s block %s rejected by %s", election_id, height, result.rejected_by)

        self._store(db, block)
        db.commit()
        log.info("election %s: sealed %s block %s with %d tx", election_id, kind, height, len(txs))
        return block

    def ensure_genesis(self, db: Session, election_id: int, params_hash: str) -> Block:
        """Create the genesis block for an election if it doesn't exist yet.

        `params_hash` = hash of the election's public setup (see
        app/services/elections.py::election_params_hash). Anchoring it at
        height 0 makes later edits to candidates/window detectable.
        """
        with self._lock:
            existing = db.scalars(
                select(ChainBlock).where(ChainBlock.election_id == election_id, ChainBlock.height == 0)
            ).first()
            if existing is not None:
                return self._row_to_block(existing, self._block_txs(db, election_id, 0))
            return self._commit_block(db, election_id, "genesis", [params_hash])

    def submit(self, election_id: int, ballot_hash: str) -> None:
        """Queue an already-stored ballot for the next block."""
        self.mempool.add(election_id, ballot_hash)

    def seal(self, db: Session, election_id: int, *, force: bool = False) -> list[Block]:
        """Seal waiting ballots into block(s).

        force=False: seal one block of up to `block_size` ballots.
        force=True : seal everything waiting (used when an election closes).
        On failure the ballots go back to the mempool marked 'failed' and are
        retried on the next tick; the error is re-raised.
        """
        sealed: list[Block] = []
        with self._lock:
            while True:
                txs = self.mempool.take(election_id, self.block_size)
                if not txs:
                    break
                # Shuffle so a ballot's position in the block says nothing
                # about when it arrived.
                self._rng.shuffle(txs)
                try:
                    sealed.append(self._commit_block(db, election_id, "ballots", txs))
                except Exception as error:
                    db.rollback()
                    self.mempool.put_back(election_id, txs, str(error))
                    log.error("sealing failed for election %s: %s", election_id, error)
                    raise
                if not force:
                    break
        return sealed

    def seal_due(self, session_factory) -> int:
        """Background-sealer tick: seal every election whose mempool is due."""
        count = 0
        for election_id in self.mempool.due(self.block_size, self.block_interval_seconds):
            with session_factory() as db:
                try:
                    count += len(self.seal(db, election_id))
                except Exception:  # already logged + requeued; keep the loop alive
                    pass
        return count

    def append_results(self, db: Session, election_id: int, results_hash: str) -> Block:
        """Append the final 'results' block. After it, the chain accepts nothing."""
        with self._lock:
            return self._commit_block(db, election_id, "results", [results_hash])

    def restore_mempool(self, db: Session) -> int:
        """Re-queue ballots that are stored but not yet in any block (after a restart)."""
        on_chain = select(BlockTransaction.tx_hash)
        rows = db.execute(
            select(Ballot.election_id, Ballot.ballot_hash).where(Ballot.ballot_hash.not_in(on_chain))
        ).all()
        for election_id, ballot_hash in rows:
            self.mempool.add(election_id, ballot_hash)
        db.rollback()
        return len(rows)

    # ================================================================ reading
    def ballot_status(self, db: Session, election_id: int, ballot_hash: str) -> dict[str, Any]:
        """Where a ballot is: pending / failed (retrying) / confirmed (+ Merkle proof)."""
        tx = db.scalars(select(BlockTransaction).where(BlockTransaction.tx_hash == ballot_hash)).first()
        if tx is None:
            state = self.mempool.state_of(election_id, ballot_hash) or "pending"
            return {"status": state, "block": None}

        txs = self._block_txs(db, tx.election_id, tx.height)
        row = db.get(ChainBlock, (tx.election_id, tx.height))
        return {
            "status": "confirmed",
            "block": {
                "height": row.height,
                "block_hash": row.block_hash,
                "merkle_root": row.merkle_root,
                "timestamp": row.timestamp,
                "sealed_by": row.sealed_by,
                "tx_count": row.tx_count,
            },
            "merkle_proof": [list(step) for step in merkle_proof(txs, tx.position)],
        }

    def status(self, db: Session, election_id: int) -> dict[str, Any]:
        head = self.db_head(db, election_id)
        return {
            "election_id": election_id,
            "height": None if head is None else head.height,
            "head_hash": None if head is None else head.block_hash,
            "finalized": head is not None and head.kind == "results",
            "pending_ballots": self.mempool.pending_count(election_id),
            "last_seal_error": self.mempool.last_error(election_id),
            "node_count": len(self.network.nodes),
            "difficulty": self.difficulty,
            "block_size": self.block_size,
        }

    def verify(self, db: Session, election_id: int) -> dict[str, Any]:
        """Full audit: each node's chain, the majority, and the DB copy."""
        network_audit = self.network.audit(election_id)
        db_blocks = self.db_chain(db, election_id)
        db_report = validate_chain(db_blocks)
        db_matches = (
            network_audit.has_majority
            and db_report.valid
            and db_report.head_hash == network_audit.canonical_head
            and db_report.length == network_audit.canonical_length
        )
        result = network_audit.to_dict()
        result["database_copy"] = {**db_report.to_dict(), "matches_majority": db_matches}
        result["healthy"] = network_audit.healthy and db_matches
        return result

    def trusted_chain(self, db: Session, election_id: int) -> list[Block]:
        """The chain the tally may rely on. Raises ChainIntegrityError otherwise.

        Requires a valid majority chain among the nodes AND an identical
        database copy. Individual out-of-sync nodes are tolerated (that is
        the point of majority consensus).
        """
        canonical = self.network.canonical_chain(election_id)
        if canonical is None:
            raise ChainIntegrityError("no majority of nodes agrees on a valid chain")
        db_blocks = self.db_chain(db, election_id)
        if [b.block_hash for b in db_blocks] != [b.block_hash for b in canonical]:
            raise ChainIntegrityError("database copy of the chain differs from the node majority")
        report = validate_chain(canonical)
        if not report.valid:
            raise ChainIntegrityError(report.error or "chain invalid")
        return canonical

    def startup_check(self, db: Session, election_ids: list[int]) -> list[str]:
        """Compare DB and nodes for every election; return human-readable problems."""
        problems = []
        for election_id in election_ids:
            report = self.verify(db, election_id)
            if not report["healthy"]:
                bad = [n["node_id"] for n in report["nodes"] if not n["in_majority"]]
                problems.append(
                    f"election {election_id}: nodes out of majority={bad}, "
                    f"db matches={report['database_copy']['matches_majority']}"
                )
        db.rollback()
        return problems


__all__ = ["ChainService", "ConsensusError", "ChainIntegrityError", "ChainFinalizedError"]
