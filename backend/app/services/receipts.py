"""Receipt verification (README: verify a vote was counted, without revealing it).

Given a receipt code, we return where the ballot is on the chain plus a
Merkle proof that anyone can check offline (docs/blockchain.md, "Verify a
receipt by hand"). We never return the candidate.

Unknown, malformed and real-but-wrong codes all get the same "not found"
answer, so the endpoint can't be used to probe for valid codes.
"""
from sqlalchemy.orm import Session

from app.blockchain.service import ChainService
from app.crypto.receipts import is_well_formed, receipt_hash
from app.models import Election, Receipt


def verify_receipt(db: Session, chain: ChainService, code: str) -> dict:
    not_found = {"valid": False, "message": "We couldn't find that receipt. Check the code and try again."}
    if not is_well_formed(code):
        return not_found
    receipt = db.get(Receipt, receipt_hash(code))
    if receipt is None:
        return not_found

    election = db.get(Election, receipt.election_id)
    location = chain.ballot_status(db, receipt.election_id, receipt.ballot_hash)
    messages = {
        "confirmed": "Receipt valid: your ballot is recorded on the chain and will be counted.",
        "pending": "Receipt valid: your ballot is recorded and waiting to be sealed into a block.",
        "failed": "Receipt valid: sealing your ballot is being retried. No action is needed.",
    }
    return {
        "valid": True,
        "election_id": receipt.election_id,
        "election_title": election.title if election else None,
        "ballot_hash": receipt.ballot_hash,
        "status": location["status"],
        "block": location.get("block"),
        "merkle_proof": location.get("merkle_proof"),
        "counted": bool(election and election.tallied_at and location["status"] == "confirmed"),
        "message": messages[location["status"]],
    }
