"""FastAPI dependencies: database session, current user, role checks, services.

Usage in a route:

    @router.post("/admin/elections")
    def create(..., user: User = Depends(require_role("election_admin"))): ...

All authorisation happens here on the server, never only in the UI
(README §8.3).
"""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.blockchain.service import ChainService
from app.config import Settings
from app.crypto.ballot import ElectionKeyStore
from app.database import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_chain(request: Request) -> ChainService:
    return request.app.state.chain


def get_keys(request: Request) -> ElectionKeyStore:
    return request.app.state.keys


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    from app.services.auth import user_for_token  # local import avoids a cycle

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_for_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str) -> Callable[[User], User]:
    """Dependency factory: 403 unless the signed-in user has one of `roles`."""
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this action")
        return user
    return checker


Chain = Annotated[ChainService, Depends(get_chain)]
Keys = Annotated[ElectionKeyStore, Depends(get_keys)]
AppSettings = Annotated[Settings, Depends(get_settings)]
