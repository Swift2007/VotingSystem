"""Create a staff account from the command line (bootstraps the first system admin).

Run from backend/:

    python -m scripts.create_admin <student_id> [role]

role defaults to system_admin (also: election_admin, auditor). The password is
asked for interactively, so it never lands in shell history. If the user
already exists, only their role is changed.

After this, a system admin can promote others over HTTP:
    PATCH /admin/users/{student_id}/role   {"role": "election_admin"}
"""
import getpass
import sys
from pathlib import Path

from sqlalchemy import select

from app import database
from app.config import settings
from app.core.audit import audit
from app.models import User
from app.models.user import ROLES
from app.services.auth import create_user


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 1
    student_id = argv[0]
    role = argv[1] if len(argv) > 1 else "system_admin"
    if role not in ROLES:
        print(f"role must be one of: {', '.join(ROLES)}")
        return 1

    if settings.database_url.startswith("sqlite:///"):
        Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    database.configure(settings.database_url)
    database.init_db()

    with database.SessionLocal() as db:
        user = db.scalars(select(User).where(User.student_id == student_id)).first()
        if user is not None:
            user.role = role
            audit(db, None, "user_role_changed", user_id=user.id, new_role=role, via="cli")
            db.commit()
            print(f"{student_id} is now {role}.")
            return 0

        password = getpass.getpass("Password (min 8 chars): ")
        if len(password) < 8 or password != getpass.getpass("Repeat password: "):
            print("Passwords must match and be at least 8 characters.")
            return 1
        user = create_user(db, student_id, password, student_id, role)
        audit(db, None, "staff_account_created", user_id=user.id, role=role, via="cli")
        db.commit()
        print(f"Created {role} {student_id}. Sign in with POST /auth/login.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
