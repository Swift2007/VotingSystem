"""Sign-up, sign-in, sessions and lockout (database-backed).

* Passwords are hashed with PBKDF2 (app/core/security.py).
* After `max_failed_logins` wrong passwords the account is locked for
  `lockout_minutes` (brute-force protection).
* Unknown student IDs still run a password hash so response time doesn't
  reveal which IDs exist.
* Self-registration always creates a *student*. Admin and auditor accounts
  are created by scripts/seed_demo.py or `create_user()`.
"""
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.core.audit import audit
from app.core.security import DUMMY_PASSWORD_HASH, hash_password, hash_token, new_token, verify_password
from app.core.timeutil import as_utc, utcnow
from app.models import AuthSession, User
from app.models.user import ROLES
from app.services.errors import BadRequest, Conflict, Locked, Unauthorized


def create_user(db: Session, student_id: str, password: str, full_name: str = "", role: str = "student") -> User:
    """Insert a user (any role). Raises Conflict if the student ID exists. Does not commit."""
    if role not in ROLES:
        raise BadRequest(f"unknown role {role!r}")
    user = User(student_id=student_id, full_name=full_name, password_hash=hash_password(password), role=role)
    db.add(user)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise Conflict("Student ID is already registered") from error
    return user


def _issue_session(db: Session, settings: Settings, user: User) -> tuple[str, object]:
    token = new_token()
    expires_at = utcnow() + timedelta(minutes=settings.token_ttl_minutes)
    db.add(AuthSession(token_hash=hash_token(token), user_id=user.id, expires_at=expires_at))
    return token, expires_at


def register(db: Session, settings: Settings, student_id: str, password: str, full_name: str = ""):
    """Create a student account and sign it in. Returns (user, token, expires_at)."""
    user = create_user(db, student_id, password, full_name, "student")
    token, expires_at = _issue_session(db, settings, user)
    audit(db, user.id, "user_registered")
    db.commit()
    return user, token, expires_at


def login(db: Session, settings: Settings, student_id: str, password: str):
    """Check credentials. Returns (user, token, expires_at) or raises Unauthorized/Locked."""
    user = db.scalars(select(User).where(User.student_id == student_id)).first()
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)  # equalise timing
        db.rollback()
        raise Unauthorized("Invalid student ID or password")

    now = utcnow()
    if user.locked_until is not None and as_utc(user.locked_until) > now:
        db.rollback()
        raise Locked("Too many failed sign-in attempts. Try again later.")

    if not verify_password(password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_logins = 0
            audit(db, user.id, "account_locked")
        db.commit()
        raise Unauthorized("Invalid student ID or password")

    user.failed_logins = 0
    user.locked_until = None
    token, expires_at = _issue_session(db, settings, user)
    if user.role != "student":
        audit(db, user.id, "staff_login", role=user.role)
    db.commit()
    return user, token, expires_at


def user_for_token(db: Session, token: str) -> User | None:
    """Resolve a bearer token to its user, or None if unknown/expired."""
    session = db.get(AuthSession, hash_token(token))
    if session is None or as_utc(session.expires_at) <= utcnow():
        return None
    return db.get(User, session.user_id)


def logout(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    db.commit()
