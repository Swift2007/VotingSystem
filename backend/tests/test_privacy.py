"""Ballot privacy and integrity (README critical req. 2 & 3, §4 Privacy/Integrity, acceptance item 4)."""
import json
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from app import database


def run(h, admin, chain, db):
    eid, cands = h.election(admin, {"President": ["Unique-Name-Ada", "Unique-Name-Ben"]})
    for s in ("stud-AAA", "stud-BBB"):
        h.user(s)
    h.voters(admin, eid, "stud-AAA", "stud-BBB")
    h.open(eid)
    codes = [h.vote(h.login(s), eid, {"President": cands["President"][i]}).json()["receipt_code"]
             for i, s in enumerate(("stud-AAA", "stud-BBB"))]
    chain.seal(db, eid, force=True)
    return eid, cands, codes


def test_no_table_links_users_to_ballots_or_receipts():
    insp = inspect(database.engine)
    for table in ("ballots", "receipts", "chain_blocks", "block_transactions"):
        cols = {c["name"] for c in insp.get_columns(table)}
        assert "user_id" not in cols and "student_id" not in cols, table
    ballot_cols = {c["name"] for c in insp.get_columns("ballots")}
    assert not {"created_at", "timestamp", "candidate_id"} & ballot_cols


def test_no_plaintext_choice_or_identity_in_chain_files(h, admin, chain, db, settings):
    eid, cands, codes = run(h, admin, chain, db)
    for path in Path(settings.chain_data_dir).rglob("*.jsonl"):
        content = path.read_text()
        for needle in ("stud-AAA", "stud-BBB", "Unique-Name", "President", *codes):
            assert needle not in content, (needle, path)
        for line in content.splitlines():
            block = json.loads(line)
            assert set(block) == {"election_id", "height", "kind", "timestamp", "prev_hash", "merkle_root",
                                  "tx_count", "nonce", "difficulty", "sealed_by", "block_hash", "transactions"}


def test_no_plaintext_choice_in_database_ballots_or_audit_log(h, admin, chain, db, settings):
    eid, cands, codes = run(h, admin, chain, db)
    raw = sqlite3.connect(settings.database_url.removeprefix("sqlite:///"))
    for (blob,) in raw.execute("SELECT encrypted_ballot FROM ballots"):
        assert b"President" not in blob and b"choices" not in blob
    log = " ".join(str(r) for r in raw.execute("SELECT actor_id, action, detail FROM audit_log"))
    for code in codes:
        assert code not in log and code.replace("-", "") not in log
    assert "President" not in log
    vote_rows = list(raw.execute("SELECT actor_id FROM audit_log WHERE action='vote_cast'"))
    assert vote_rows and all(actor is None for (actor,) in vote_rows)


@pytest.mark.parametrize("table", ["ballots", "voter_status", "receipts", "chain_blocks", "block_transactions", "audit_log"])
def test_vote_tables_are_append_only(h, admin, chain, db, table):
    run(h, admin, chain, db)
    with pytest.raises(Exception, match="append-only"):
        with database.engine.begin() as conn:
            conn.execute(text(f"DELETE FROM {table}"))
    with pytest.raises(Exception, match="append-only"):
        with database.engine.begin() as conn:
            col = {"ballots": "election_id", "voter_status": "election_id", "receipts": "election_id",
                   "chain_blocks": "nonce", "block_transactions": "position", "audit_log": "action"}[table]
            conn.execute(text(f"UPDATE {table} SET {col} = {col}"))


def test_audit_helper_refuses_secrets(db):
    from app.core.audit import AuditLeakError, audit
    for bad in ("password", "receipt_code", "choices", "token"):
        with pytest.raises(AuditLeakError):
            audit(db, None, "x", **{bad: "secret"})
    audit(db, None, "ok", voters_added=3)  # allowed
    db.rollback()


def test_ballot_key_never_in_database(h, admin, settings):
    eid, _ = h.election(admin)
    key_hex = (Path(settings.election_keys_dir) / f"election_{eid}.key").read_text().strip()
    raw = Path(settings.database_url.removeprefix("sqlite:///")).read_bytes()
    assert key_hex.encode() not in raw and bytes.fromhex(key_hex) not in raw
