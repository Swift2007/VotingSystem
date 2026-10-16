"""/chain: public read access to the simulated blockchain, plus dev-only demo tools.

Everything here is safe to show anyone: the chain holds only hashes.
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.blockchain.errors import ConsensusError
from app.core.audit import audit
from app.core.deps import AppSettings, Chain, DbSession, require_role
from app.models import ChainBlock, User
from app.schemas.chain import BlockOut, TamperRequest
from app.services.elections import get_election
from app.services.errors import Conflict, NotFound

router = APIRouter(prefix="/chain", tags=["chain"])

SystemAdmin = Annotated[User, Depends(require_role("system_admin"))]


@router.get("/{election_id}/status")
def chain_status(election_id: int, db: DbSession, chain: Chain) -> dict[str, Any]:
    get_election(db, election_id)
    return chain.status(db, election_id)


@router.get("/{election_id}/blocks", response_model=list[BlockOut])
def list_blocks(election_id: int, db: DbSession, chain: Chain,
                offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500)) -> list[BlockOut]:
    """Block headers, genesis first (no transaction lists, to keep it light)."""
    blocks = chain.db_chain(db, election_id)[offset:offset + limit]
    return [BlockOut(**{**b.to_dict(), "transactions": None}) for b in blocks]


@router.get("/{election_id}/blocks/{height}", response_model=BlockOut)
def get_block(election_id: int, height: int, db: DbSession, chain: Chain) -> BlockOut:
    if db.get(ChainBlock, (election_id, height)) is None:
        raise NotFound("Block not found")
    block = chain.db_chain(db, election_id)[height]
    return BlockOut(**block.to_dict())


@router.get("/{election_id}/verify")
def verify_chain(election_id: int, db: DbSession, chain: Chain) -> dict[str, Any]:
    """Validate every node's copy, find the majority, and compare the DB copy."""
    get_election(db, election_id)
    return chain.verify(db, election_id)


@router.post("/{election_id}/resync")
def resync(election_id: int, admin: SystemAdmin, db: DbSession, chain: Chain) -> dict[str, Any]:
    """Repair out-of-sync nodes by copying the majority chain onto them."""
    try:
        repaired = chain.network.resync(election_id)
    except ConsensusError as error:
        raise Conflict(str(error)) from error
    audit(db, admin.id, "chain_resync", election_id=election_id, nodes=repaired)
    db.commit()
    return {"repaired": repaired, "verify": chain.verify(db, election_id)}


@router.post("/{election_id}/simulate/tamper")
def tamper(election_id: int, payload: TamperRequest, admin: SystemAdmin, db: DbSession, chain: Chain,
           settings: AppSettings) -> dict[str, Any]:
    """DEV ONLY (ENABLE_SIMULATION_TOOLS=true): corrupt one node to demo detection."""
    if not settings.enable_simulation_tools:
        raise NotFound("Not found")
    try:
        description = chain.network.node(payload.node_id).tamper(election_id, payload.height, payload.mode)
    except KeyError as error:
        raise NotFound("Unknown node") from error
    except ValueError as error:
        raise Conflict(str(error)) from error
    audit(db, admin.id, "chain_tamper_simulated", election_id=election_id, node=payload.node_id, mode=payload.mode)
    db.commit()
    return {"tampered": description, "verify": chain.verify(db, election_id)}
