"""Voting rules: README critical requirements 1 (one vote), 4 (close) and §3 eligibility/validation."""
import threading

from app import database
from app.models import Ballot, VoterStatus
from app.services.voting import cast_vote


def setup_open(h, admin, *students):
    eid, cands = h.election(admin)
    for s in students:
        h.user(s)
    if students:
        h.voters(admin, eid, *students)
    h.open(eid)
    return eid, cands


def ballot(cands, p=0, t=0):
    return {"President": cands["President"][p], "Treasurer": cands["Treasurer"][t]}


def test_eligible_student_votes_once_and_gets_receipt(h, admin, db):
    eid, cands = setup_open(h, admin, "s1")
    voter = h.login("s1")
    assert h.client.get(f"/elections/{eid}", headers=voter).json()["status"] == "open"

    r = h.vote(voter, eid, ballot(cands))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["receipt_code"].startswith("VC-") and body["status"] == "pending"
    assert h.client.get(f"/elections/{eid}/me", headers=voter).json() == {"election_id": eid, "eligible": True, "has_voted": True}

    again = h.vote(voter, eid, ballot(cands, 1, 1))
    assert again.status_code == 409
    assert db.query(Ballot).count() == 1


def test_concurrent_submissions_create_exactly_one_ballot(h, admin, app):
    """20 simultaneous requests from one student → one accepted ballot (acceptance item 3)."""
    eid, cands = setup_open(h, admin, "s1")
    with database.SessionLocal() as db:
        from app.models import User
        user = db.query(User).filter_by(student_id="s1").one()
        db.expunge(user)

    outcomes: list[str] = []
    lock = threading.Lock()

    def worker():
        with database.SessionLocal() as session:
            try:
                cast_vote(session, app.state.chain, app.state.keys, user, eid, ballot(cands))
                result = "ok"
            except Exception as error:  # Conflict expected for all but one
                result = type(error).__name__
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes.count("ok") == 1, outcomes
    assert set(outcomes) <= {"ok", "Conflict"}
    with database.SessionLocal() as db:
        assert db.query(Ballot).count() == 1
        assert db.query(VoterStatus).count() == 1


def test_ineligible_and_non_student_cannot_vote(h, admin):
    eid, cands = setup_open(h, admin, "s1")
    outsider = h.user("s2")
    assert h.vote(outsider, eid, ballot(cands)).status_code == 403
    assert h.vote(admin, eid, ballot(cands)).status_code == 403


def test_voting_outside_the_window_is_rejected(h, admin):
    eid, cands = h.election(admin)
    voter = h.user("s1")
    h.voters(admin, eid, "s1")
    r = h.vote(voter, eid, ballot(cands))
    assert r.status_code == 403 and "not opened" in r.json()["detail"]

    h.expire(eid)
    r = h.vote(voter, eid, ballot(cands))
    assert r.status_code == 403 and "closed" in r.json()["detail"]


def test_admin_close_stops_voting(h, admin):
    eid, cands = setup_open(h, admin, "s1", "s2")
    assert h.vote(h.login("s1"), eid, ballot(cands)).status_code == 201
    assert h.client.post(f"/admin/elections/{eid}/close", headers=admin).status_code == 200
    assert h.vote(h.login("s2"), eid, ballot(cands)).status_code == 403


def test_server_side_ballot_validation(h, admin):
    eid, cands = setup_open(h, admin, "s1")
    voter = h.login("s1")
    other_eid, other = h.election(admin, {"President": ["Zed"]})

    cases = [
        {"President": cands["President"][0]},                                  # missing position
        {**ballot(cands), "Mascot": 1},                                        # unknown position
        {"President": cands["Treasurer"][0], "Treasurer": cands["Treasurer"][1]},  # wrong position
        {"President": other["President"][0], "Treasurer": cands["Treasurer"][0]},  # other election
    ]
    for choices in cases:
        r = h.vote(voter, eid, choices)
        assert r.status_code == 400, (choices, r.text)
    # Nothing was recorded, so a valid vote still works.
    assert h.vote(voter, eid, ballot(cands)).status_code == 201


def test_setup_is_frozen_once_open(h, admin):
    eid, cands = setup_open(h, admin)
    r = h.client.post(f"/admin/elections/{eid}/candidates", headers=admin, json={"full_name": "Late", "position": "President"})
    assert r.status_code == 409
    assert h.client.patch(f"/admin/elections/{eid}", headers=admin, json={"title": "x"}).status_code == 409
