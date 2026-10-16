"""Casting a vote (README critical requirements 1-4).

Order of operations for POST /elections/{id}/vote:

 1. Only students may vote; the election must be *open* by the server clock.
 2. The student must be on the eligibility list.
 3. Ballot validated server-side: exactly one candidate for every position,
    and each candidate really stands for that position in this election.
 4. Genesis block is ensured (first vote of the election anchors its setup).
 5. ONE database transaction (SQLite BEGIN IMMEDIATE):
      a. INSERT voter_status(election, user). The primary key makes a second
         insert fail, which is the one-person-one-vote guarantee, even for
         two simultaneous requests.
      b. Encrypt choices (AES-GCM, per-election key) and INSERT the ballot
         with a random id and NO user id.
      c. Generate the receipt code; INSERT only its hash with the ballot hash.
      d. Audit "vote_cast" with the election id only (no user, no ballot).
    Commit. Either all of a-d happen or none do.
 6. Hand the ballot hash to the chain mempool. Status starts as "pending"
    and becomes "confirmed" when its block is sealed.

The receipt code is returned exactly once and is never logged.
"""
import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.blockchain.service import ChainService
from app.core.audit import audit
from app.crypto.ballot import ElectionKeyStore, ballot_hash
from app.crypto.receipts import new_receipt_code, receipt_hash
from app.models import Ballot, EligibleVoter, Receipt, User, VoterStatus
from app.services.elections import effective_status, election_params_hash, get_election, positions
from app.services.errors import BadRequest, Conflict, Forbidden


def validate_ballot(allowed: dict[str, set[int]], choices: dict[str, int]) -> dict[str, int]:
    """Return the cleaned ballot or raise BadRequest with a clear message."""
    if not allowed:
        raise BadRequest("This election has no candidates")
    missing = sorted(set(allowed) - set(choices))
    extra = sorted(set(choices) - set(allowed))
    if extra:
        raise BadRequest(f"Unknown position(s): {', '.join(extra)}")
    if missing:
        raise BadRequest(f"Choose a candidate for: {', '.join(missing)}")
    for position, candidate_id in choices.items():
        if candidate_id not in allowed[position]:
            raise BadRequest(f"That candidate is not standing for {position}")
    return {p: int(c) for p, c in choices.items()}


def _check_can_vote(db: Session, user: User, election_id: int) -> None:
    election = get_election(db, election_id)
    if user.role != "student":
        raise Forbidden("Only students can vote")
    status = effective_status(election)
    if status == "upcoming":
        raise Forbidden("Voting has not opened yet")
    if status == "closed":
        raise Forbidden("Voting is closed for this election")
    if db.get(EligibleVoter, (election_id, user.id)) is None:
        raise Forbidden("You are not on the voter list for this election")
    if db.get(VoterStatus, (election_id, user.id)) is not None:
        raise Conflict("You have already voted in this election")


def cast_vote(db: Session, chain: ChainService, keys: ElectionKeyStore, user: User,
              election_id: int, choices: dict[str, int]) -> dict:
    # Steps 1-4: checks (cheap, user-friendly errors) + genesis.
    _check_can_vote(db, user, election_id)
    clean = validate_ballot(positions(db, election_id), choices)
    params_hash = election_params_hash(db, get_election(db, election_id))
    db.rollback()
    chain.ensure_genesis(db, election_id, params_hash)

    # Step 5: atomic write. Re-check inside the transaction, because the
    # election may have closed while we were building the genesis block.
    db.expire_all()  # reload rows from the DB, not the session cache
    _check_can_vote(db, user, election_id)
    db.add(VoterStatus(election_id=election_id, user_id=user.id))
    try:
        db.flush()
    except IntegrityError as error:  # a concurrent request won the race
        db.rollback()
        raise Conflict("You have already voted in this election") from error

    encrypted = keys.encrypt(election_id, clean)
    ballot_id = secrets.token_hex(16)
    b_hash = ballot_hash(ballot_id, encrypted)
    db.add(Ballot(ballot_id=ballot_id, election_id=election_id, encrypted_ballot=encrypted, ballot_hash=b_hash))

    code = new_receipt_code()
    db.add(Receipt(receipt_hash=receipt_hash(code), election_id=election_id, ballot_hash=b_hash))
    audit(db, None, "vote_cast", election_id=election_id)
    db.commit()

    # Step 6: queue for the next block.
    chain.submit(election_id, b_hash)
    return {
        "receipt_code": code,
        "ballot_hash": b_hash,
        "status": "pending",
        "message": "Your vote has been recorded. It is waiting to be sealed into the next block.",
    }
