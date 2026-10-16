from pydantic import BaseModel, Field


class BlockOut(BaseModel):
    election_id: int
    height: int
    kind: str
    timestamp: str
    prev_hash: str
    merkle_root: str
    tx_count: int
    nonce: int
    difficulty: int
    sealed_by: str
    block_hash: str
    transactions: list[str] | None = None


class TamperRequest(BaseModel):
    node_id: str = Field(examples=["node-2"])
    height: int = Field(default=0, ge=0)
    mode: str = Field(default="edit", pattern="^(edit|remine|drop)$")
