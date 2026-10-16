"""UTC time helpers.

SQLite has no time-zone type, so `DateTime(timezone=True)` columns come back
*naive*. Everything in this app is UTC, so `as_utc()` re-attaches UTC before
any comparison. Never compare a naive and an aware datetime directly.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
