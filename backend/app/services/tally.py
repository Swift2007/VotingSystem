"""Counting votes after close (README critical requirement 5).

Steps:
 1. Election must be closed and not yet tallied.
 2. Make sure every stored ballot is sealed (requeue + force seal).
 3. Get the *trusted* chain: majority of nodes agree, every block valid,
    database copy identical. Otherwise refuse (ChainIntegrityError → 409).
 4. The counted set is the ballot hashes ON THE CHAIN. Any ballot row that
    isn't on the chain, or chain entry with no ballot row, is a discrepancy
    and stops the tally.
 5. Decrypt each ballot and count. A ballot that fails to decrypt or doesn't
    match the candidate list is counted as *invalid*, never silently dropped.
    Zero-vote candidates are listed with 0. Ties are reported, not broken
    (decision D-007).
 6. Build the results document (counts + decrypted ballots in SORTED order),
    hash it, append it as the final "results" block, then store Result rows.
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blockchain.chain import ballot_transactions
from app.blockchain.errors import ChainIntegrityError
from app.blockchain.hashing import canonical_json, hash_object
from app.blockchain.service import ChainService
from app.core.audit import audit
from app.core.timeutil import utcnow
from app.crypto.ballot import BallotDecryptionError, ElectionKeyStore
from app.models import Ballot, Candidate, Election, Result, User
from app.services.admin import close_election
from app.services.elections import effective_status, get_election, positions
from app.services.errors import Conflict


def count_ballots(allowed: dict[str, set[int]], decrypted: list[dict[str, int] | None]) -> tuple[dict[int, int], int, list[dict]]:
    """Pure counting function (unit-tested with ties/invalid/zero-vote cases).

    `decrypted` holds one entry per on-chain ballot: its choices, or None if
    it couldn't be decrypted. Returns (counts per candidate, invalid count,
    list of valid ballots).
    """
    counts = {cid: 0 for cids in allowed.values() for cid in cids}
    invalid = 0
    valid_ballots = []
    for choices in decrypted:
        if (
            choices is None
            or set(choices) != set(allowed)
            or any(cid not in allowed[pos] for pos, cid in choices.items())
        ):
            invalid += 1
            continue
        for cid in choices.values():
            counts[cid] += 1
        valid_ballots.append(choices)
    return counts, invalid, valid_ballots


def run_tally(db: Session, chain: ChainService, keys: ElectionKeyStore, actor: User | None, election_id: int) -> Election:
    election = get_election(db, election_id)
    if effective_status(election) != "closed":
        raise Conflict("The election must be closed before counting")
    if election.tallied_at is not None:
        raise Conflict("This election has already been counted")

    close_election(db, chain, actor, election_id)  # idempotent; seals everything

    try:
        trusted = chain.trusted_chain(db, election_id)
    except ChainIntegrityError as error:
        raise Conflict(f"Chain verification failed, so counting was refused: {error}") from error
    if trusted and trusted[-1].kind == "results":
        raise Conflict("This election's chain is already finalised")

    on_chain = ballot_transactions(trusted)
    rows = {b.ballot_hash: b for b in db.scalars(select(Ballot).where(Ballot.election_id == election_id))}
    missing_rows = set(on_chain) - set(rows)
    off_chain = set(rows) - set(on_chain)
    if missing_rows or off_chain:
        raise Conflict(
            f"Ballot box and chain disagree ({len(missing_rows)} on chain without a ballot, "
            f"{len(off_chain)} ballots not on chain); counting refused"
        )

    allowed = positions(db, election_id)
    decrypted: list[dict[str, int] | None] = []
    for h in on_chain:
        try:
            decrypted.append(keys.decrypt(election_id, rows[h].encrypted_ballot))
        except BallotDecryptionError:
            decrypted.append(None)
    counts, invalid, valid_ballots = count_ballots(allowed, decrypted)

    document = {
        "election_id": election_id,
        "total_ballots": len(on_chain),
        "invalid_ballots": invalid,
        "counts": {str(cid): n for cid, n in sorted(counts.items())},
        # Sorted canonically: the order carries no information about who/when.
        "ballots": sorted(valid_ballots, key=lambda b: canonical_json(b)),
    }
    results_hash = hash_object(document)
    db.rollback()
    results_block = chain.append_results(db, election_id, results_hash)

    election = get_election(db, election_id)
    for cid, n in counts.items():
        db.add(Result(election_id=election_id, candidate_id=cid, vote_count=n))
    election.tallied_at = utcnow()
    election.total_ballots = len(on_chain)
    election.invalid_ballots = invalid
    election.results_hash = results_hash
    election.results_document = canonical_json(document).decode("utf-8")
    audit(db, actor.id if actor else None, "election_tallied", election_id=election_id,
          results_block=results_block.height)
    db.commit()
    return election


def results_view(db: Session, chain: ChainService, election: Election) -> dict:
    """Published results grouped by position, with winners and tie flags."""
    document = json.loads(election.results_document or "{}")
    counts = {int(k): v for k, v in document.get("counts", {}).items()}
    by_position: dict[str, list[Candidate]] = {}
    for c in db.scalars(select(Candidate).where(Candidate.election_id == election.id).order_by(Candidate.id)):
        by_position.setdefault(c.position, []).append(c)

    position_results = []
    for position, cands in sorted(by_position.items()):
        rows = sorted(
            ({"candidate_id": c.id, "full_name": c.full_name, "votes": counts.get(c.id, 0)} for c in cands),
            key=lambda r: (-r["votes"], r["candidate_id"]),
        )
        top = rows[0]["votes"] if rows else 0
        winners = [r["candidate_id"] for r in rows if top > 0 and r["votes"] == top]
        position_results.append({
            "position": position,
            "candidates": rows,
            "winner_ids": winners,
            "tie": len(winners) > 1,
        })

    head = chain.db_head(db, election.id)
    return {
        "election_id": election.id,
        "title": election.title,
        "published_at": election.published_at,
        "total_ballots": election.total_ballots,
        "invalid_ballots": election.invalid_ballots,
        "results_hash": election.results_hash,
        "results_block": None if head is None or head.kind != "results" else {
            "height": head.height, "block_hash": head.block_hash, "merkle_root": head.merkle_root,
        },
        "positions": position_results,
        "results_document": election.results_document,
    }
