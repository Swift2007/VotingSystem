"""Tables used by the STUDENT (voter): eligibility, voted-status, receipt.
Nothing here stores WHAT the student chose."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class EligibleVoter(Base):
    __tablename__ = "eligible_voters"

    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)


class VoterStatus(Base):
    """WHO has voted. The composite primary key blocks a second vote."""
    __tablename__ = "voter_status"

    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Receipt(Base):
    """Student keeps the code. We store only its hash."""
    __tablename__ = "receipts"

    receipt_hash: Mapped[str] = mapped_column(String, primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), nullable=False)
    ballot_hash: Mapped[str] = mapped_column(String, nullable=False)
