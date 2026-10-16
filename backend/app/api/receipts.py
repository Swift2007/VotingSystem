"""/receipts: public receipt verification."""
from fastapi import APIRouter, Request

from app.core.deps import Chain, DbSession
from app.schemas.vote import ReceiptVerifyRequest, ReceiptVerifyResponse
from app.services.receipts import verify_receipt

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("/verify", response_model=ReceiptVerifyResponse)
def verify(payload: ReceiptVerifyRequest, request: Request, db: DbSession, chain: Chain) -> ReceiptVerifyResponse:
    """Check a receipt code. POST (not GET) so codes never end up in URLs or access logs."""
    request.app.state.limiter.check(request, "receipt")
    return ReceiptVerifyResponse(**verify_receipt(db, chain, payload.code))
