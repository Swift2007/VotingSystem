"""/admin: election-admin and auditor functions. Every route checks the role on the server."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.elections import election_out
from app.core.deps import Chain, DbSession, Keys, require_role
from app.models import User
from app.schemas.auth import RoleUpdate, UserResponse
from app.schemas.elections import (
    AuditEntryOut, CandidateCreate, CandidateOut, CandidateUpdate, ElectionCreate, ElectionOut,
    ElectionUpdate, TurnoutOut, VotersAdd, VotersAddResult,
)
from app.services import admin as admin_service
from app.services.elections import get_election, turnout
from app.services.tally import results_view, run_tally

router = APIRouter(prefix="/admin", tags=["admin"])

ElectionAdmin = Annotated[User, Depends(require_role("election_admin"))]
SystemAdmin = Annotated[User, Depends(require_role("system_admin"))]
Overseer = Annotated[User, Depends(require_role("election_admin", "auditor", "system_admin"))]


@router.post("/elections", response_model=ElectionOut, status_code=status.HTTP_201_CREATED)
def create_election(payload: ElectionCreate, admin: ElectionAdmin, db: DbSession, keys: Keys) -> ElectionOut:
    election = admin_service.create_election(db, keys, admin, payload.title, payload.opens_at, payload.closes_at)
    return election_out(db, election)


@router.patch("/elections/{election_id}", response_model=ElectionOut)
def update_election(election_id: int, payload: ElectionUpdate, admin: ElectionAdmin, db: DbSession) -> ElectionOut:
    election = admin_service.update_election(db, admin, election_id, **payload.model_dump())
    return election_out(db, election)


@router.post("/elections/{election_id}/candidates", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
def add_candidate(election_id: int, payload: CandidateCreate, admin: ElectionAdmin, db: DbSession) -> CandidateOut:
    return CandidateOut.model_validate(
        admin_service.add_candidate(db, admin, election_id, payload.full_name, payload.position, payload.manifesto)
    )


@router.patch("/elections/{election_id}/candidates/{candidate_id}", response_model=CandidateOut)
def update_candidate(election_id: int, candidate_id: int, payload: CandidateUpdate, admin: ElectionAdmin,
                     db: DbSession) -> CandidateOut:
    return CandidateOut.model_validate(
        admin_service.update_candidate(db, admin, election_id, candidate_id, **payload.model_dump())
    )


@router.delete("/elections/{election_id}/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(election_id: int, candidate_id: int, admin: ElectionAdmin, db: DbSession) -> None:
    admin_service.delete_candidate(db, admin, election_id, candidate_id)


@router.post("/elections/{election_id}/voters", response_model=VotersAddResult)
def add_voters(election_id: int, payload: VotersAdd, admin: ElectionAdmin, db: DbSession) -> VotersAddResult:
    return VotersAddResult(**admin_service.add_voters(db, admin, election_id, payload.student_ids))


@router.get("/elections/{election_id}/turnout", response_model=TurnoutOut)
def get_turnout(election_id: int, user: Overseer, db: DbSession) -> TurnoutOut:
    get_election(db, election_id)
    return TurnoutOut(election_id=election_id, **turnout(db, election_id))


@router.post("/elections/{election_id}/close")
def close_election(election_id: int, admin: ElectionAdmin, db: DbSession, chain: Chain) -> dict[str, Any]:
    """Stop voting now and seal every waiting ballot into the chain."""
    return admin_service.close_election(db, chain, admin, election_id)


@router.post("/elections/{election_id}/tally")
def tally(election_id: int, admin: ElectionAdmin, db: DbSession, chain: Chain, keys: Keys) -> dict[str, Any]:
    """Verify the chain, count, and append the results block. Results stay private until published."""
    election = run_tally(db, chain, keys, admin, election_id)
    return results_view(db, chain, election)


@router.post("/elections/{election_id}/publish", response_model=ElectionOut)
def publish(election_id: int, admin: ElectionAdmin, db: DbSession) -> ElectionOut:
    return election_out(db, admin_service.publish_results(db, admin, election_id))


@router.patch("/users/{student_id}/role", response_model=UserResponse)
def set_role(student_id: str, payload: RoleUpdate, admin: SystemAdmin, db: DbSession) -> UserResponse:
    """Make a user an election_admin / auditor / system_admin (or back to student)."""
    return UserResponse.model_validate(admin_service.set_user_role(db, admin, student_id, payload.role))


@router.get("/audit-log", response_model=list[AuditEntryOut])
def audit_log(user: Overseer, db: DbSession,
              limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)) -> list[AuditEntryOut]:
    return [AuditEntryOut.model_validate(e) for e in admin_service.audit_entries(db, limit, offset)]
