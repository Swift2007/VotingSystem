from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AuthCredentials(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("student_id", mode="before")
    @classmethod
    def trim_student_id(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RegisterRequest(AuthCredentials):
    pass


class LoginRequest(AuthCredentials):
    pass


class UserResponse(BaseModel):
    student_id: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse