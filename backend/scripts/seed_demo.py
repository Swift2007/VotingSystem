"""Seed a demo election so the whole flow can be tried locally.

Run from backend/:  python -m scripts.seed_demo

Creates (password for every account: demo-password):
  admin       election_admin
  sysadmin    system_admin
  auditor     auditor
  student01 … student10   students, all eligible
and an election "Student Council 2026 (demo)" that is OPEN for 2 hours, with
candidates for President and Treasurer.

Idempotent for users (existing ones are kept); creates a new election each run.
"""
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from app import database
from app.config import settings
from app.core.timeutil import utcnow
from app.crypto.ballot import ElectionKeyStore
from app.models import User
from app.services import admin as admin_service
from app.services.auth import create_user
from app.services.errors import Conflict

PASSWORD = "demo-password"


def main() -> None:
    if settings.database_url.startswith("sqlite:///"):
        Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    database.configure(settings.database_url)
    database.init_db()
    keys = ElectionKeyStore(settings.election_keys_dir)

    with database.SessionLocal() as db:
        accounts = [("admin", "election_admin"), ("sysadmin", "system_admin"), ("auditor", "auditor")]
        accounts += [(f"student{i:02d}", "student") for i in range(1, 11)]
        for student_id, role in accounts:
            try:
                create_user(db, student_id, PASSWORD, student_id.title(), role)
                db.commit()
            except Conflict:
                db.rollback()

        admin = db.scalars(select(User).where(User.student_id == "admin")).one()
        now = utcnow()
        election = admin_service.create_election(
            db, keys, admin, "Student Council 2026 (demo)", now + timedelta(minutes=1), now + timedelta(hours=2)
        )
        for name, position in [("Amara Phiri", "President"), ("Brian Tembo", "President"),
                               ("Chipo Banda", "Treasurer"), ("Daniel Mwale", "Treasurer"),
                               ("Esther Zulu", "Treasurer")]:
            admin_service.add_candidate(db, admin, election.id, name, position, f"Manifesto of {name}.")
        admin_service.add_voters(db, admin, election.id, [f"student{i:02d}" for i in range(1, 11)])

        # Open it right away (a real admin would wait for opens_at).
        election.opens_at = utcnow() - timedelta(seconds=1)
        db.commit()
        print(f"Election {election.id} is open until {election.closes_at:%H:%M} UTC.")
        print(f"Accounts: admin / sysadmin / auditor / student01..student10, password '{PASSWORD}'")


if __name__ == "__main__":
    main()
