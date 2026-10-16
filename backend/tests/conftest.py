"""Shared fixtures. Every test gets a fresh database, node directory and key directory."""
import os
import tempfile

# Must be set before `app` is imported anywhere (app.main builds a default app at import).
_BOOT_DIR = tempfile.mkdtemp(prefix="votex-boot-")
os.environ.setdefault("PASSWORD_HASH_ITERATIONS", "1000")
os.environ["DATABASE_URL"] = f"sqlite:///{_BOOT_DIR}/boot.db"
os.environ["CHAIN_DATA_DIR"] = f"{_BOOT_DIR}/nodes"
os.environ["ELECTION_KEYS_DIR"] = f"{_BOOT_DIR}/keys"
os.environ["SEALER_ENABLED"] = "false"

from datetime import timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import database  # noqa: E402
from app.config import Settings  # noqa: E402
from app.core.timeutil import utcnow  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Election  # noqa: E402
from app.services.auth import create_user  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        chain_data_dir=str(tmp_path / "nodes"),
        election_keys_dir=str(tmp_path / "keys"),
        node_count=3,
        block_size=3,
        block_interval_seconds=3600,
        pow_difficulty=1,
        sealer_enabled=False,
        enable_simulation_tools=True,
        rate_limit_per_minute=1000,
    )


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def chain(app):
    return app.state.chain


@pytest.fixture
def keys(app):
    return app.state.keys


@pytest.fixture
def db(app):
    with database.SessionLocal() as session:
        yield session


class Helpers:
    """Small helpers so tests read like the user story they check."""

    def __init__(self, client: TestClient):
        self.client = client

    def user(self, student_id: str, role: str = "student") -> dict:
        with database.SessionLocal() as db:
            create_user(db, student_id, PASSWORD, f"Name {student_id}", role)
            db.commit()
        return self.login(student_id)

    def login(self, student_id: str) -> dict:
        r = self.client.post("/auth/login", json={"student_id": student_id, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def election(self, admin: dict, positions: dict[str, list[str]] | None = None) -> tuple[int, dict[str, list[int]]]:
        """Create an upcoming election with candidates. Returns (id, {position: [candidate ids]})."""
        positions = positions or {"President": ["Ada", "Ben"], "Treasurer": ["Cy", "Di", "Ed"]}
        now = utcnow()
        r = self.client.post("/admin/elections", headers=admin, json={
            "title": "Student Council 2026",
            "opens_at": (now + timedelta(hours=1)).isoformat(),
            "closes_at": (now + timedelta(hours=5)).isoformat(),
        })
        assert r.status_code == 201, r.text
        eid = r.json()["id"]
        ids: dict[str, list[int]] = {}
        for position, names in positions.items():
            for name in names:
                c = self.client.post(f"/admin/elections/{eid}/candidates", headers=admin,
                                     json={"full_name": name, "position": position})
                assert c.status_code == 201, c.text
                ids.setdefault(position, []).append(c.json()["id"])
        return eid, ids

    @staticmethod
    def open(eid: int) -> None:
        """Move the voting window so the election is open now (test-only shortcut)."""
        with database.SessionLocal() as db:
            e = db.get(Election, eid)
            e.opens_at = utcnow() - timedelta(minutes=1)
            db.commit()

    @staticmethod
    def expire(eid: int) -> None:
        """Move the closing time into the past without pressing 'close'."""
        with database.SessionLocal() as db:
            e = db.get(Election, eid)
            e.opens_at = utcnow() - timedelta(hours=2)
            e.closes_at = utcnow() - timedelta(seconds=1)
            db.commit()

    def voters(self, admin: dict, eid: int, *student_ids: str) -> None:
        r = self.client.post(f"/admin/elections/{eid}/voters", headers=admin, json={"student_ids": list(student_ids)})
        assert r.status_code == 200, r.text

    def vote(self, headers: dict, eid: int, choices: dict[str, int]):
        return self.client.post(f"/elections/{eid}/vote", headers=headers, json={"choices": choices})


@pytest.fixture
def h(client) -> Helpers:
    return Helpers(client)


@pytest.fixture
def admin(h) -> dict:
    return h.user("admin-1", "election_admin")
