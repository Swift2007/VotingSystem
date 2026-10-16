"""/elections: public election + candidate pages, voter state, voting, results."""
from typing import Any

from fastapi import APIRouter

from app.core.deps import Chain, CurrentUser, DbSession, Keys
from app.models import Election
from app.schemas.elections import CandidateOut, ElectionOut, VoterStateOut
from app.schemas.vote import VoteRequest, VoteResponse
from app.services import elections as election_service
from app.services.errors import NotFound
from app.services.tally import results_view
from app.services.voting import cast_vote

router = APIRouter(prefix="/elections", tags=["elections"])


def election_out(db, election: Election) -> ElectionOut:
    return ElectionOut(
        id=election.id,
        title=election.title,
        status=election_service.effective_status(election),
        opens_at=election.opens_at,
        closes_at=election.closes_at,
        positions=sorted(election_service.positions(db, election.id)),
        key_fingerprint=election.key_fingerprint,
        tallied=election.tallied_at is not None,
        results_published=election.published_at is not None,
    )


@router.get("", response_model=list[ElectionOut])
def list_elections(db: DbSession) -> list[ElectionOut]:
    return [election_out(db, e) for e in election_service.list_elections(db)]


@router.get("/{election_id}", response_model=ElectionOut)
def get_election(election_id: int, db: DbSession) -> ElectionOut:
    return election_out(db, election_service.get_election(db, election_id))


@router.get("/{election_id}/candidates", response_model=list[CandidateOut])
def list_candidates(election_id: int, db: DbSession) -> list[CandidateOut]:
    election_service.get_election(db, election_id)
    return [CandidateOut.model_validate(c) for c in election_service.candidates(db, election_id)]


@router.get("/{election_id}/me", response_model=VoterStateOut)
def my_state(election_id: int, user: CurrentUser, db: DbSession) -> VoterStateOut:
    """Is the signed-in user eligible, and have they voted? (Never *how*.)"""
    election_service.get_election(db, election_id)
    return VoterStateOut(election_id=election_id, **election_service.voter_state(db, election_id, user.id))


@router.post("/{election_id}/vote", response_model=VoteResponse, status_code=201)
def vote(election_id: int, payload: VoteRequest, user: CurrentUser, db: DbSession, chain: Chain, keys: Keys) -> VoteResponse:
    """Cast the signed-in student's single ballot. See app/services/voting.py."""
    return VoteResponse(**cast_vote(db, chain, keys, user, election_id, payload.choices))


@router.get("/{election_id}/results")
def results(election_id: int, db: DbSession, chain: Chain) -> dict[str, Any]:
    """Published results (404 until the election admin publishes them)."""
    election = election_service.get_election(db, election_id)
    if election.published_at is None:
        raise NotFound("Results have not been published yet")
    return results_view(db, chain, election)
