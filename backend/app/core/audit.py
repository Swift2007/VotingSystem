"""Audit log helper.

`audit(db, actor_id, action, **detail)` adds an AuditLog row in the caller's
transaction (committed with the action it describes).

Hard rule (README §3, §8.3): the audit log never holds secret votes,
passwords, tokens or receipt codes. `audit()` refuses any detail key that
looks like one, so a careless call fails in tests instead of leaking.
"""
import json

from sqlalchemy.orm import Session

from app.models import AuditLog

# Compared against each "_"-separated word of a detail key, so "receipt_code"
# and "choices" are refused but "voters_added" is fine.
FORBIDDEN_WORDS = {
    "password", "token", "choice", "choices", "ballot", "ballots", "receipt", "code", "vote", "key", "secret",
}


class AuditLeakError(ValueError):
    """Raised when someone tries to log a forbidden field."""


def audit(db: Session, actor_id: int | None, action: str, **detail: object) -> None:
    for name in detail:
        if FORBIDDEN_WORDS.intersection(name.lower().split("_")):
            raise AuditLeakError(f"refusing to write {name!r} to the audit log")
    db.add(AuditLog(
        actor_id=actor_id,
        action=action,
        detail=json.dumps(detail, sort_keys=True, default=str) if detail else None,
    ))
