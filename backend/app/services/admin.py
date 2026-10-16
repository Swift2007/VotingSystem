"""Election-admin actions: elections, candidates, voter lists, close, publish.

Rules enforced here (server side):
* Elections and candidates can only be edited while the election is
  *upcoming*. Once voting opens, the setup is anchored in the genesis block.
* There is deliberately NO function to edit or delete a ballot, receipt or
  vote status (README §4 Integrity). The database triggers back this up.
* Every admin action is written to the audit log.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blockchain.service import ChainService
from app.core.audit import audit
from app.core.timeutil import as_utc, utcnow
from app.crypto.ballot import ElectionKeyStore
from app.models import AuditLog, Candidate, Election, EligibleVoter, User
from app.services.elections import effective_status, election_params_hash, get_election
from app.services.errors import BadRequest, Conflict, NotFound


def _require_upcoming(election: Election) -> None:
    if effective_status(election) != "upcoming":
        raise Conflict("This election has already opened; its setup can no longer change")


def _check_window(opens_at: datetime, closes_at: datetime) -> None:
    if as_utc(closes_at) <= as_utc(opens_at):
        raise BadRequest("closes_at must be after opens_at")


# ------------------------------------------------------------------ elections
def create_election(db: Session, keys: ElectionKeyStore, actor: User, title: str,
                    opens_at: datetime, closes_at: datetime) -> Election:
    _check_window(opens_at, closes_at)
    election = Election(title=title, opens_at=as_utc(opens_at), closes_at=as_utc(closes_at), status="upcoming")
    db.add(election)
    db.flush()  # assigns election.id
    election.key_fingerprint = keys.create(election.id)
    audit(db, actor.id, "election_created", election_id=election.id, title=title)
    db.commit()
    return election


def update_election(db: Session, actor: User, election_id: int, *, title: str | None = None,
                    opens_at: datetime | None = None, closes_at: datetime | None = None) -> Election:
    election = get_election(db, election_id)
    _require_upcoming(election)
    new_open = as_utc(opens_at) if opens_at else as_utc(election.opens_at)
    new_close = as_utc(closes_at) if closes_at else as_utc(election.closes_at)
    _check_window(new_open, new_close)
    if title is not None:
        election.title = title
    election.opens_at, election.closes_at = new_open, new_close
    audit(db, actor.id, "election_updated", election_id=election_id)
    db.commit()
    return election


# ----------------------------------------------------------------- candidates
def add_candidate(db: Session, actor: User, election_id: int, full_name: str, position: str,
                  manifesto: str | None) -> Candidate:
    election = get_election(db, election_id)
    _require_upcoming(election)
    candidate = Candidate(election_id=election_id, full_name=full_name, position=position, manifesto=manifesto)
    db.add(candidate)
    db.flush()
    audit(db, actor.id, "candidate_added", election_id=election_id, candidate_id=candidate.id)
    db.commit()
    return candidate


def _get_candidate(db: Session, election_id: int, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None or candidate.election_id != election_id:
        raise NotFound("Candidate not found")
    return candidate


def update_candidate(db: Session, actor: User, election_id: int, candidate_id: int, **fields) -> Candidate:
    _require_upcoming(get_election(db, election_id))
    candidate = _get_candidate(db, election_id, candidate_id)
    for name in ("full_name", "position", "manifesto"):
        if fields.get(name) is not None:
            setattr(candidate, name, fields[name])
    audit(db, actor.id, "candidate_updated", election_id=election_id, candidate_id=candidate_id)
    db.commit()
    return candidate


def delete_candidate(db: Session, actor: User, election_id: int, candidate_id: int) -> None:
    _require_upcoming(get_election(db, election_id))
    candidate = _get_candidate(db, election_id, candidate_id)
    db.delete(candidate)
    audit(db, actor.id, "candidate_removed", election_id=election_id, candidate_id=candidate_id)
    db.commit()


# ------------------------------------------------------------------ voter list
def add_voters(db: Session, actor: User, election_id: int, student_ids: list[str]) -> dict[str, list[str]]:
    """Make students eligible. Allowed until the election closes; never removes anyone."""
    election = get_election(db, election_id)
    if effective_status(election) == "closed":
        raise Conflict("This election is closed")
    wanted = sorted({s.strip() for s in student_ids if s.strip()})
    users = {u.student_id: u for u in db.scalars(select(User).where(User.student_id.in_(wanted)))}
    added, already, unknown, not_student = [], [], [], []
    for sid in wanted:
        user = users.get(sid)
        if user is None:
            unknown.append(sid)
        elif user.role != "student":
            not_student.append(sid)
        elif db.get(EligibleVoter, (election_id, user.id)) is not None:
            already.append(sid)
        else:
            db.add(EligibleVoter(election_id=election_id, user_id=user.id))
            added.append(sid)
    audit(db, actor.id, "voters_added", election_id=election_id, count=len(added))
    db.commit()
    return {"added": added, "already_eligible": already, "unknown": unknown, "not_student": not_student}


# --------------------------------------------------------------- close/publish
def close_election(db: Session, chain: ChainService, actor: User | None, election_id: int) -> dict:
    """Stop voting now (or confirm the time-based close) and seal every waiting ballot."""
    election = get_election(db, election_id)
    status = effective_status(election)
    if status == "upcoming":
        raise Conflict("This election has not opened yet")
    params_hash = election_params_hash(db, election)
    if election.status != "closed":
        election.status = "closed"
        audit(db, actor.id if actor else None, "election_closed", election_id=election_id)
        db.commit()
    chain.ensure_genesis(db, election_id, params_hash)  # elections with zero votes still get a chain
    requeue_unsealed(db, chain, election_id)
    sealed = chain.seal(db, election_id, force=True)
    return {"election_id": election_id, "status": "closed", "blocks_sealed": len(sealed)}


def requeue_unsealed(db: Session, chain: ChainService, election_id: int) -> None:
    """Put any stored-but-unsealed ballot back in the mempool (crash/race safety)."""
    from app.models import Ballot, BlockTransaction

    rows = db.scalars(
        select(Ballot.ballot_hash).where(
            Ballot.election_id == election_id,
            Ballot.ballot_hash.not_in(select(BlockTransaction.tx_hash)),
        )
    ).all()
    for ballot_hash in rows:
        chain.submit(election_id, ballot_hash)
    db.rollback()


def publish_results(db: Session, actor: User, election_id: int) -> Election:
    election = get_election(db, election_id)
    if election.tallied_at is None:
        raise Conflict("Run the tally before publishing results")
    if election.published_at is None:
        election.published_at = utcnow()
        audit(db, actor.id, "results_published", election_id=election_id)
        db.commit()
    return election


# ----------------------------------------------------------------------- users
def set_user_role(db: Session, actor: User, student_id: str, role: str) -> User:
    """Change a user's role (system_admin only; checked by the route).

    You can't change your own role. That stops the last system admin from
    accidentally locking everyone out of user management.
    """
    from app.models.user import ROLES

    if role not in ROLES:
        raise BadRequest(f"Role must be one of: {', '.join(ROLES)}")
    user = db.scalars(select(User).where(User.student_id == student_id)).first()
    if user is None:
        raise NotFound("User not found")
    if user.id == actor.id:
        raise Conflict("You cannot change your own role")
    if user.role != role:
        old_role, user.role = user.role, role
        audit(db, actor.id, "user_role_changed", user_id=user.id, old_role=old_role, new_role=role)
        db.commit()
    return user


def audit_entries(db: Session, limit: int = 200, offset: int = 0) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).offset(offset).limit(limit)))
