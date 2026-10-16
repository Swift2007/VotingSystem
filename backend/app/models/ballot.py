"""The secret ballot box. It lives in its own file, with NO user_id,
NO timestamp and a random id, so a ballot can never be traced to a voter.

`encrypted_ballot` is AES-GCM ciphertext (see app/crypto/ballot.py).
`ballot_hash` = sha256(ballot_id || encrypted_ballot) is the only thing that
goes on the simulated blockchain.
"""
from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Ballot(Base):
    __tablename__ = "ballots"
    __table_args__ = {"sqlite_with_rowid": False}  # no hidden row order

    ballot_id: Mapped[str] = mapped_column(String, primary_key=True)  # secrets.token_hex(16)
    election_id: Mapped[int] = mapped_column(
        ForeignKey("elections.id"), nullable=False, index=True
    )
    encrypted_ballot: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ballot_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
