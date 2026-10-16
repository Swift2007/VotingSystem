"""Election queries and the rules for an election's status.

`effective_status()` is the ONLY place that decides whether voting is open.
It is computed from the server clock each time, never trusted from the
stored column, so an election closes exactly at `closes_at` even if no
one presses "close" (README critical requirement 4).
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.blockchain.hashing import hash_object
from app.core.timeutil import as_utc, utcnow
from app.models import Candidate, Election, EligibleVoter, VoterStatus
from app.services.errors import NotFound


def effective_status(election: Election, now=None) -> str:
    now = now or utcnow()
    if election.status == "closed" or now >= as_utc(election.closes_at):
        return "closed"
    if now >= as_utc(election.opens_at):
        return "open"
    return "upcoming"


def get_election(db: Session, election_id: int) -> Election:
    election = db.get(Election, election_id)
    if election is None:
        raise NotFound("Election not found")
    return election


def list_elections(db: Session) -> list[Election]:
    return list(db.scalars(select(Election).order_by(Election.opens_at.desc())))


def candidates(db: Session, election_id: int) -> list[Candidate]:
    return list(db.scalars(
        select(Candidate).where(Candidate.election_id == election_id)
        .order_by(Candidate.position, Candidate.id)
    ))


def positions(db: Session, election_id: int) -> dict[str, set[int]]:
    """{position name: {candidate ids}} - the shape a valid ballot must match."""
    result: dict[str, set[int]] = {}
    for c in candidates(db, election_id):
        result.setdefault(c.position, set()).add(c.id)
    return result


def voter_state(db: Session, election_id: int, user_id: int) -> dict[str, bool]:
    return {
        "eligible": db.get(EligibleVoter, (election_id, user_id)) is not None,
        "has_voted": db.get(VoterStatus, (election_id, user_id)) is not None,
    }


def turnout(db: Session, election_id: int) -> dict[str, int]:
    eligible = db.scalar(select(func.count()).select_from(EligibleVoter).where(EligibleVoter.election_id == election_id))
    voted = db.scalar(select(func.count()).select_from(VoterStatus).where(VoterStatus.election_id == election_id))
    return {"eligible": eligible or 0, "voted": voted or 0}


def election_params_hash(db: Session, election: Election) -> str:
    """Hash of the election's public setup; becomes the genesis transaction.

    Includes title, voting window, every candidate (id, name, position) and
    the encryption key fingerprint. If any of these change after voting
    starts, the recomputed hash no longer matches the genesis block.
    """
    return hash_object({
        "election_id": election.id,
        "title": election.title,
        "opens_at": as_utc(election.opens_at).isoformat(),
        "closes_at": as_utc(election.closes_at).isoformat(),
        "key_fingerprint": election.key_fingerprint,
        "candidates": [
            {"id": c.id, "full_name": c.full_name, "position": c.position}
            for c in sorted(candidates(db, election.id), key=lambda c: c.id)
        ],
    })
