"""Shared login tables for ALL roles (student, election_admin, system_admin, auditor).

One table + a role column = one login system, no duplicated code.
Passwords and session tokens are stored only as hashes.
"""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

ROLES = ("student", "election_admin", "system_admin", "auditor")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('student','election_admin','system_admin','auditor')",
            name="ck_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    password_hash: Mapped[str] = mapped_column(String, nullable=False)  # "pbkdf2_sha256$iter$salt$hash"
    role: Mapped[str] = mapped_column(String, nullable=False, default="student", server_default="student")
    failed_logins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuthSession(Base):
    """A signed-in session. Only the SHA-256 of the bearer token is stored,
    so a database leak does not leak usable tokens."""
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
