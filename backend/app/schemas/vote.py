from typing import Any

from pydantic import BaseModel, Field


class VoteRequest(BaseModel):
    # {"President": 3, "Treasurer": 7}: one candidate id per position.
    choices: dict[str, int] = Field(min_length=1, max_length=50)


class VoteResponse(BaseModel):
    receipt_code: str        # shown ONCE; the server keeps only its hash
    ballot_hash: str
    status: str              # "pending" until sealed into a block
    message: str


class ReceiptVerifyRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)


class ReceiptVerifyResponse(BaseModel):
    valid: bool
    message: str
    election_id: int | None = None
    election_title: str | None = None
    ballot_hash: str | None = None
    status: str | None = None                 # pending | failed | confirmed
    block: dict[str, Any] | None = None
    merkle_proof: list[list[str]] | None = None
    counted: bool | None = None
