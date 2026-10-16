"""Admin access control, audit log, and the public chain API + tamper demo
(README §3 Admin panel / Audit log, acceptance item 9; docs/blockchain.md "Tamper demo")."""


def test_non_admins_cannot_reach_admin_functions(h, admin):
    eid, _ = h.election(admin)
    student = h.user("s1")
    auditor = h.user("aud", "auditor")
    sysadmin = h.user("sys", "system_admin")
    for headers in (student, auditor, sysadmin, {}):
        assert h.client.post("/admin/elections", headers=headers, json={
            "title": "x", "opens_at": "2030-01-01T00:00:00Z", "closes_at": "2030-01-02T00:00:00Z"}).status_code in (401, 403)
        assert h.client.post(f"/admin/elections/{eid}/close", headers=headers).status_code in (401, 403)
    # Auditors and system admins may *read* the audit log; students may not.
    assert h.client.get("/admin/audit-log", headers=auditor).status_code == 200
    assert h.client.get("/admin/audit-log", headers=sysadmin).status_code == 200
    assert h.client.get("/admin/audit-log", headers=student).status_code == 403


def test_admin_actions_appear_in_audit_log(h, admin):
    eid, _ = h.election(admin)
    h.user("s1")
    h.voters(admin, eid, "s1", "ghost")
    actions = [e["action"] for e in h.client.get("/admin/audit-log", headers=admin).json()]
    assert {"election_created", "candidate_added", "voters_added"} <= set(actions)


def test_voter_list_reports_unknown_ids(h, admin):
    eid, _ = h.election(admin)
    h.user("s1")
    r = h.client.post(f"/admin/elections/{eid}/voters", headers=admin, json={"student_ids": ["s1", "ghost", "admin-1"]})
    assert r.json() == {"added": ["s1"], "already_eligible": [], "unknown": ["ghost"], "not_student": ["admin-1"]}
    t = h.client.get(f"/admin/elections/{eid}/turnout", headers=admin).json()
    assert t == {"election_id": eid, "eligible": 1, "voted": 0}


def voted_election(h, admin, chain, db, n=4):
    eid, cands = h.election(admin)
    students = [f"s{i}" for i in range(n)]
    for s in students:
        h.user(s)
    h.voters(admin, eid, *students)
    h.open(eid)
    for s in students:
        h.vote(h.login(s), eid, {"President": cands["President"][0], "Treasurer": cands["Treasurer"][1]})
    chain.seal(db, eid, force=True)
    return eid


def test_public_chain_endpoints(h, admin, chain, db):
    eid = voted_election(h, admin, chain, db)
    status = h.client.get(f"/chain/{eid}/status").json()
    assert status["height"] == 2 and status["pending_ballots"] == 0 and status["node_count"] == 3

    blocks = h.client.get(f"/chain/{eid}/blocks").json()
    assert [b["kind"] for b in blocks] == ["genesis", "ballots", "ballots"]
    assert all(b["transactions"] is None for b in blocks)
    assert blocks[1]["prev_hash"] == blocks[0]["block_hash"]
    assert len(h.client.get(f"/chain/{eid}/blocks/1").json()["transactions"]) == 3
    assert h.client.get(f"/chain/{eid}/blocks/99").status_code == 404

    verify = h.client.get(f"/chain/{eid}/verify").json()
    assert verify["healthy"] and verify["database_copy"]["matches_majority"]


def test_tamper_demo_detect_then_resync(h, admin, chain, db):
    eid = voted_election(h, admin, chain, db)
    sysadmin = h.user("sys", "system_admin")
    assert h.client.post(f"/chain/{eid}/simulate/tamper", headers=admin, json={"node_id": "node-2"}).status_code == 403

    r = h.client.post(f"/chain/{eid}/simulate/tamper", headers=sysadmin,
                      json={"node_id": "node-2", "height": 1, "mode": "edit"}).json()
    assert not r["verify"]["healthy"]
    node2 = next(n for n in r["verify"]["nodes"] if n["node_id"] == "node-2")
    assert not node2["valid"] and node2["first_bad_height"] == 1
    assert r["verify"]["database_copy"]["matches_majority"]  # majority still intact

    fixed = h.client.post(f"/chain/{eid}/resync", headers=sysadmin).json()
    assert fixed["repaired"] == ["node-2"] and fixed["verify"]["healthy"]


def test_tamper_tool_hidden_when_disabled(h, admin, chain, db, app):
    eid = voted_election(h, admin, chain, db, n=1)
    sysadmin = h.user("sys", "system_admin")
    object.__setattr__(app.state.settings, "enable_simulation_tools", False)
    r = h.client.post(f"/chain/{eid}/simulate/tamper", headers=sysadmin, json={"node_id": "node-1"})
    assert r.status_code == 404


def test_database_tamper_is_detected(h, admin, chain, db):
    """Editing the DB copy (bypassing triggers) is caught by comparing against the nodes."""
    from app import database
    eid = voted_election(h, admin, chain, db)
    with database.engine.begin() as conn:
        conn.exec_driver_sql("DROP TRIGGER trg_block_transactions_no_update")
        conn.exec_driver_sql(
            f"UPDATE block_transactions SET tx_hash = '{'f' * 64}' WHERE election_id = {eid} AND height = 1 AND position = 0"
        )
    verify = h.client.get(f"/chain/{eid}/verify").json()
    assert not verify["healthy"] and not verify["database_copy"]["matches_majority"]


def test_restart_restores_unsealed_ballots(h, admin, settings):
    """Ballots accepted but not yet sealed survive a restart (README: never lose a recorded vote)."""
    from fastapi.testclient import TestClient

    from app.main import create_app
    eid, cands = h.election(admin)
    h.user("s1")
    h.voters(admin, eid, "s1")
    h.open(eid)
    h.vote(h.login("s1"), eid, {"President": cands["President"][0], "Treasurer": cands["Treasurer"][0]})

    with TestClient(create_app(settings)) as fresh:
        assert fresh.get(f"/chain/{eid}/status").json()["pending_ballots"] == 1


def test_system_admin_can_promote_a_user(h, admin):
    """PATCH /admin/users/{id}/role: system_admin only, audited, takes effect on the next request."""
    sysadmin = h.user("sys", "system_admin")
    student = h.user("s1")

    r = h.client.patch("/admin/users/s1/role", headers=sysadmin, json={"role": "election_admin"})
    assert r.status_code == 200 and r.json()["role"] == "election_admin"
    # Same token, new powers: the role is looked up on every request.
    assert h.client.get("/admin/audit-log", headers=student).status_code == 200

    actions = [e["action"] for e in h.client.get("/admin/audit-log", headers=sysadmin).json()]
    assert "user_role_changed" in actions


def test_only_system_admin_can_change_roles(h, admin):
    student = h.user("s1")
    auditor = h.user("aud", "auditor")
    for headers in ({}, student, admin, auditor):
        r = h.client.patch("/admin/users/s1/role", headers=headers, json={"role": "system_admin"})
        assert r.status_code in (401, 403)
    assert h.client.get("/auth/me", headers=student).json()["role"] == "student"


def test_role_change_validation(h):
    sysadmin = h.user("sys", "system_admin")
    assert h.client.patch("/admin/users/ghost/role", headers=sysadmin, json={"role": "auditor"}).status_code == 404
    assert h.client.patch("/admin/users/sys/role", headers=sysadmin, json={"role": "student"}).status_code == 409
    h.user("s1")
    assert h.client.patch("/admin/users/s1/role", headers=sysadmin, json={"role": "king"}).status_code == 422
