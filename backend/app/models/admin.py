"""Tables managed by the ELECTION ADMIN: elections and their final results."""
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
    status: Mapped[str] = mapped_column(String, nullable=False, default="upcoming", server_default="upcoming")
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    public_key: Mapped[str | None] = mapped_column(Text)  # encrypts ballots


class Result(Base):
    """Written once after the election closes."""
    __tablename__ = "results"

    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), primary_key=True)
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False)
