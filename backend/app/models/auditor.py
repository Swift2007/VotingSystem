"""Tables the AUDITOR / OBSERVER can inspect: hash chain and audit log.
Neither contains a vote choice or a link between voter and choice."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ChainBlock(Base):
    __tablename__ = "chain_blocks"

    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), primary_key=True)
    height: Mapped[int] = mapped_column(Integer, primary_key=True)
    ballot_hash: Mapped[str] = mapped_column(String, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String, nullable=False)
    block_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)  # NEVER votes/passwords/tokens
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
