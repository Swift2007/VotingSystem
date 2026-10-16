"""/auth: register, login, logout, current user."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import AppSettings, CurrentUser, DbSession, bearer_scheme
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession, settings: AppSettings) -> AuthResponse:
    """Create a *student* account and sign in."""
    user, token, expires_at = auth_service.register(db, settings, payload.student_id, payload.password, payload.full_name)
    return AuthResponse(access_token=token, expires_at=expires_at, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: DbSession, settings: AppSettings) -> AuthResponse:
    request.app.state.limiter.check(request, "login")
    user, token, expires_at = auth_service.login(db, settings, payload.student_id, payload.password)
    return AuthResponse(access_token=token, expires_at=expires_at, user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user: CurrentUser,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    auth_service.logout(db, credentials.credentials)


@router.get("/me", response_model=UserResponse)
def get_current_user(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
