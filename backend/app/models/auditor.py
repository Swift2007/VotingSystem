"""Tables the AUDITOR / OBSERVER can inspect: the hash chain and the audit log.

Neither contains a vote choice or a link between voter and choice.

`ChainBlock` + `BlockTransaction` are the app's indexed *read copy* of the
simulated blockchain. The authoritative copies are the per-node JSONL files
managed by app/blockchain/node.py; startup and /chain/{id}/verify compare the two.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ChainBlock(Base):
    __tablename__ = "chain_blocks"

    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), primary_key=True)
    height: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # genesis | ballots | results
    timestamp: Mapped[str] = mapped_column(String, nullable=False)  # UTC ISO-8601, seconds
    prev_hash: Mapped[str] = mapped_column(String, nullable=False)
    merkle_root: Mapped[str] = mapped_column(String, nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False)
    nonce: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    sealed_by: Mapped[str] = mapped_column(String, nullable=False)
    block_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class BlockTransaction(Base):
    """One leaf of a block's Merkle tree, in the (shuffled) order it was sealed."""
    __tablename__ = "block_transactions"
    __table_args__ = {"sqlite_with_rowid": False}

    election_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    height: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)  # JSON; NEVER votes/passwords/tokens
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
