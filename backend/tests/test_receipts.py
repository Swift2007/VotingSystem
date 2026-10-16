"""Receipts: pending → confirmed, Merkle proof checks out, choice never revealed (acceptance items 5, 6)."""
from app.blockchain.merkle import verify_proof
from app.models import Receipt


def vote_once(h, admin, n_students=1):
    eid, cands = h.election(admin)
    ids = [f"s{i}" for i in range(n_students)]
    for s in ids:
        h.user(s)
    h.voters(admin, eid, *ids)
    h.open(eid)
    codes = []
    for s in ids:
        r = h.vote(h.login(s), eid, {"President": cands["President"][0], "Treasurer": cands["Treasurer"][0]})
        codes.append(r.json()["receipt_code"])
    return eid, cands, codes


def test_receipt_pending_then_confirmed_with_valid_proof(h, admin, chain, db):
    eid, cands, (code,) = vote_once(h, admin)

    pending = h.client.post("/receipts/verify", json={"code": code}).json()
    assert pending["valid"] and pending["status"] == "pending" and pending["block"] is None

    chain.seal(db, eid, force=True)
    confirmed = h.client.post("/receipts/verify", json={"code": code.lower().replace("-", " ")}).json()
    assert confirmed["status"] == "confirmed"
    block = confirmed["block"]
    assert verify_proof(confirmed["ballot_hash"], confirmed["merkle_proof"], block["merkle_root"])

    # The proof matches the public block too.
    public = h.client.get(f"/chain/{eid}/blocks/{block['height']}").json()
    assert public["merkle_root"] == block["merkle_root"] and confirmed["ballot_hash"] in public["transactions"]

    # Nothing about the choice is in the answer.
    text = str(confirmed)
    for cid in cands["President"] + cands["Treasurer"]:
        assert f"'candidate_id': {cid}" not in text
    assert "President" not in text


def test_blocks_are_batched(h, admin, chain, db, settings):
    eid, _, codes = vote_once(h, admin, n_students=7)
    sealed = chain.seal(db, eid, force=True)
    assert [b.tx_count for b in sealed] == [3, 3, 1]  # block_size=3
    heights = {h.client.post("/receipts/verify", json={"code": c}).json()["block"]["height"] for c in codes}
    assert heights == {1, 2, 3}


def test_unknown_or_malformed_codes_look_the_same(h, admin):
    vote_once(h, admin)
    a = h.client.post("/receipts/verify", json={"code": "VC-AAAA-BBBB-CCCC"}).json()
    b = h.client.post("/receipts/verify", json={"code": "hello"}).json()
    assert a == b and a["valid"] is False


def test_only_the_receipt_hash_is_stored(h, admin, db):
    _, _, (code,) = vote_once(h, admin)
    stored = db.query(Receipt).one()
    assert code not in stored.receipt_hash and stored.receipt_hash != code
