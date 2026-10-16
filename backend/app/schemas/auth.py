from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthCredentials(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("student_id", mode="before")
    @classmethod
    def trim_student_id(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RegisterRequest(AuthCredentials):
    full_name: str = Field(default="", max_length=120)


class LoginRequest(AuthCredentials):
    pass


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    full_name: str
    role: str


class RoleUpdate(BaseModel):
    role: Literal["student", "election_admin", "system_admin", "auditor"]


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserResponse
