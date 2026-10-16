"""Sign-in and roles (README §3 "Sign-in and eligibility check", §4 Security)."""
from app.models import User
from tests.conftest import PASSWORD


def test_register_login_me_logout(client):
    r = client.post("/auth/register", json={"student_id": " s-100 ", "password": PASSWORD, "full_name": "Sam"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["student_id"] == "s-100" and body["user"]["role"] == "student"

    login = client.post("/auth/login", json={"student_id": "s-100", "password": PASSWORD})
    token = login.json()["access_token"]
    assert token != body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).json()["full_name"] == "Sam"

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_duplicate_registration_and_bad_credentials(client):
    client.post("/auth/register", json={"student_id": "s-1", "password": PASSWORD})
    assert client.post("/auth/register", json={"student_id": "s-1", "password": PASSWORD}).status_code == 409
    assert client.post("/auth/login", json={"student_id": "s-1", "password": "wrong-password"}).status_code == 401
    assert client.post("/auth/login", json={"student_id": "nobody", "password": PASSWORD}).status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_password_is_hashed_and_token_not_stored(client, db):
    r = client.post("/auth/register", json={"student_id": "s-2", "password": PASSWORD})
    user = db.query(User).filter_by(student_id="s-2").one()
    assert PASSWORD not in user.password_hash and user.password_hash.startswith("pbkdf2_sha256$")
    from app.models import AuthSession
    assert all(s.token_hash != r.json()["access_token"] for s in db.query(AuthSession))


def test_lockout_after_repeated_failures(client, settings):
    client.post("/auth/register", json={"student_id": "s-3", "password": PASSWORD})
    for _ in range(settings.max_failed_logins):
        client.post("/auth/login", json={"student_id": "s-3", "password": "wrong-password"})
    r = client.post("/auth/login", json={"student_id": "s-3", "password": PASSWORD})
    assert r.status_code == 423


def test_self_registration_cannot_create_admins(client):
    r = client.post("/auth/register", json={"student_id": "sneaky", "password": PASSWORD, "role": "system_admin"})
    assert r.json()["user"]["role"] == "student"
