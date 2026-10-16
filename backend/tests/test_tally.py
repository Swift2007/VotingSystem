"""Counting (README critical req. 5, §4 Correctness, acceptance item 8)."""
from app import database
from app.blockchain.hashing import hash_object
from app.models import Ballot
from app.services.tally import count_ballots

ALLOWED = {"President": {1, 2, 3}, "Treasurer": {4, 5}}


def test_count_with_tie_invalid_and_zero_votes():
    decrypted = [
        {"President": 1, "Treasurer": 4},
        {"President": 2, "Treasurer": 4},
        {"President": 1, "Treasurer": 5},
        {"President": 2, "Treasurer": 4},
        None,                                  # undecryptable
        {"President": 9, "Treasurer": 4},      # unknown candidate
        {"President": 1},                      # missing position
    ]
    counts, invalid, valid = count_ballots(ALLOWED, decrypted)
    assert counts == {1: 2, 2: 2, 3: 0, 4: 3, 5: 1}  # 1 and 2 tie; 3 has zero votes
    assert invalid == 3 and len(valid) == 4


def test_count_with_no_ballots():
    counts, invalid, valid = count_ballots(ALLOWED, [])
    assert counts == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0} and invalid == 0 and valid == []


def run_election(h, admin, votes: list[tuple[int, int]]):
    eid, cands = h.election(admin, {"President": ["Ada", "Ben", "Cal"], "Treasurer": ["Di", "Ed"]})
    students = [f"s{i}" for i in range(len(votes))]
    for s in students:
        h.user(s)
    if students:
        h.voters(admin, eid, *students)
    h.open(eid)
    for s, (p, t) in zip(students, votes):
        r = h.vote(h.login(s), eid, {"President": cands["President"][p], "Treasurer": cands["Treasurer"][t]})
        assert r.status_code == 201
    return eid, cands


def test_end_to_end_tally_matches_dataset(h, admin, chain, db):
    """Ada 2, Ben 2 (tie), Cal 0; Di 3, Ed 1. Cross-checked against an independent count."""
    dataset = [(0, 0), (1, 0), (0, 1), (1, 0)]
    eid, cands = run_election(h, admin, dataset)

    assert h.client.post(f"/admin/elections/{eid}/tally", headers=admin).status_code == 409  # still open
    assert h.client.get(f"/elections/{eid}/results").status_code == 404

    h.expire(eid)
    r = h.client.post(f"/admin/elections/{eid}/tally", headers=admin)
    assert r.status_code == 200, r.text
    assert h.client.get(f"/elections/{eid}/results").status_code == 404  # not published yet
    assert h.client.post(f"/admin/elections/{eid}/publish", headers=admin).status_code == 200

    res = h.client.get(f"/elections/{eid}/results").json()
    pres = next(p for p in res["positions"] if p["position"] == "President")
    tres = next(p for p in res["positions"] if p["position"] == "Treasurer")
    by_name = {c["full_name"]: c["votes"] for c in pres["candidates"] + tres["candidates"]}
    assert by_name == {"Ada": 2, "Ben": 2, "Cal": 0, "Di": 3, "Ed": 1}
    assert pres["tie"] and set(pres["winner_ids"]) == set(cands["President"][:2])
    assert not tres["tie"] and tres["winner_ids"] == [cands["Treasurer"][0]]
    assert res["total_ballots"] == 4 and res["invalid_ballots"] == 0

    # The results are anchored in the final block of the chain.
    import json
    assert hash_object(json.loads(res["results_document"])) == res["results_hash"]
    head = h.client.get(f"/chain/{eid}/status").json()
    assert head["finalized"] and res["results_block"]["block_hash"] == head["head_hash"]
    assert h.client.get(f"/chain/{eid}/verify").json()["healthy"]

    # Second tally is refused.
    assert h.client.post(f"/admin/elections/{eid}/tally", headers=admin).status_code == 409


def test_zero_vote_election_still_tallies(h, admin):
    eid, _ = run_election(h, admin, [])
    h.expire(eid)
    r = h.client.post(f"/admin/elections/{eid}/tally", headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["total_ballots"] == 0
    assert all(not p["winner_ids"] for p in r.json()["positions"])


def test_corrupted_ciphertext_counts_as_invalid(h, admin, keys):
    """A ballot whose ciphertext was damaged is reported as invalid, not dropped (tests bypass the trigger)."""
    eid, _ = run_election(h, admin, [(0, 0), (1, 1)])
    with database.engine.begin() as conn:
        conn.exec_driver_sql("DROP TRIGGER trg_ballots_no_update")
    with database.SessionLocal() as db:
        b = db.query(Ballot).first()
        b.encrypted_ballot = b.encrypted_ballot[:-1] + bytes([b.encrypted_ballot[-1] ^ 1])
        db.commit()
    h.expire(eid)
    r = h.client.post(f"/admin/elections/{eid}/tally", headers=admin)
    assert r.status_code == 200
    assert r.json()["invalid_ballots"] == 1 and r.json()["total_ballots"] == 2


def test_tally_refused_when_majority_chain_is_broken(h, admin, chain):
    eid, _ = run_election(h, admin, [(0, 0), (1, 1)])
    h.expire(eid)
    h.client.post(f"/admin/elections/{eid}/close", headers=admin)
    chain.network.node("node-1").tamper(eid, 1, "edit")
    chain.network.node("node-2").tamper(eid, 1, "edit")
    r = h.client.post(f"/admin/elections/{eid}/tally", headers=admin)
    assert r.status_code == 409 and "Chain verification failed" in r.json()["detail"]


def test_tally_tolerates_a_single_bad_node(h, admin, chain):
    eid, _ = run_election(h, admin, [(0, 0), (1, 1), (2, 0)])
    h.expire(eid)
    h.client.post(f"/admin/elections/{eid}/close", headers=admin)
    chain.network.node("node-3").tamper(eid, 1, "remine")
    r = h.client.post(f"/admin/elections/{eid}/tally", headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["total_ballots"] == 3


def test_auto_finalize_counts_after_closing_time(h, admin, app):
    from app.main import auto_finalize
    eid, _ = run_election(h, admin, [(0, 0)])
    h.expire(eid)
    auto_finalize(app.state.chain, app.state.keys, {})
    assert h.client.get(f"/elections/{eid}").json()["tallied"] is True
