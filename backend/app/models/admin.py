"""Tables managed by the ELECTION ADMIN: elections and their final results.

The ballot encryption key is NOT stored here. It lives in a key file outside
the database (see app/crypto/ballot.py); only its fingerprint is kept so
auditors can confirm which key an election used.
"""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Election(Base):
    __tablename__ = "elections"
    __table_args__ = (
        CheckConstraint("status IN ('upcoming','open','closed')", name="ck_elections_status"),
        CheckConstraint("closes_at > opens_at", name="ck_elections_window"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    # Stored status is only a *floor*: 'closed' here means an admin closed it
    # early. The live status is always computed from the clock as well
    # (see app/services/elections.py::effective_status).
    status: Mapped[str] = mapped_column(String, nullable=False, default="upcoming", server_default="upcoming")
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    key_fingerprint: Mapped[str | None] = mapped_column(String)  # sha256 of the ballot key
    tallied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalid_ballots: Mapped[int | None] = mapped_column(Integer)
    total_ballots: Mapped[int | None] = mapped_column(Integer)
    results_hash: Mapped[str | None] = mapped_column(String)  # anchored in the final chain block
    # Canonical JSON of the tally (counts + decrypted ballots in SORTED order,
    # so the order reveals nothing). sha256 of it == results_hash.
    results_document: Mapped[str | None] = mapped_column(Text)


class Result(Base):
    """Written once by the tally after the election closes."""
    __tablename__ = "results"

    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), primary_key=True)
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False)
