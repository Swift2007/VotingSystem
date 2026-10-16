"""Tables used by the STUDENT (voter): eligibility, voted-status, receipt.

Nothing here stores WHAT the student chose, and nothing links a user to a
ballot or a receipt:
* `VoterStatus` says *who* voted (needed for one-person-one-vote).
* `Receipt` says *which ballot* a receipt code belongs to, with no user column.
"""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EligibleVoter(Base):
    __tablename__ = "eligible_voters"

    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)


class VoterStatus(Base):
    """WHO has voted. The composite primary key blocks a second vote, even
    when two requests arrive at the same instant (README critical req. 1).
    WITHOUT ROWID so insertion order can't be lined up with the ballot table."""
    __tablename__ = "voter_status"
    __table_args__ = {"sqlite_with_rowid": False}

    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Receipt(Base):
    """The student keeps the receipt code. We store only its hash."""
    __tablename__ = "receipts"
    __table_args__ = {"sqlite_with_rowid": False}

    receipt_hash: Mapped[str] = mapped_column(String, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), nullable=False)
    ballot_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
