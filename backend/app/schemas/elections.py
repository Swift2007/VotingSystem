from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    election_id: int
    full_name: str
    position: str
    manifesto: str | None = None


class ElectionOut(BaseModel):
    id: int
    title: str
    status: str                      # upcoming | open | closed (computed from the clock)
    opens_at: datetime
    closes_at: datetime
    positions: list[str]
    key_fingerprint: str | None
    tallied: bool
    results_published: bool


class VoterStateOut(BaseModel):
    election_id: int
    eligible: bool
    has_voted: bool


class ElectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    opens_at: datetime
    closes_at: datetime

    @model_validator(mode="after")
    def window(self):
        if self.closes_at <= self.opens_at:
            raise ValueError("closes_at must be after opens_at")
        return self


class ElectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    opens_at: datetime | None = None
    closes_at: datetime | None = None


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    position: str = Field(min_length=1, max_length=80)
    manifesto: str | None = Field(default=None, max_length=5000)


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    position: str | None = Field(default=None, min_length=1, max_length=80)
    manifesto: str | None = Field(default=None, max_length=5000)


class VotersAdd(BaseModel):
    student_ids: list[str] = Field(min_length=1, max_length=5000)


class VotersAddResult(BaseModel):
    added: list[str]
    already_eligible: list[str]
    unknown: list[str]
    not_student: list[str]


class TurnoutOut(BaseModel):
    election_id: int
    eligible: int
    voted: int


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    detail: str | None
    created_at: datetime
