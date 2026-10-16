# Changelog

Short entries per build step: what changed, what's tested, what's open (README §8.3).

## 2026-10-16 · backend: make-admin route

### Changed
* `PATCH /admin/users/{student_id}/role` (system_admin token required, audited, can't change own role).
* `python -m scripts.create_admin <student_id> [role]` to bootstrap the first system admin (password prompted).
* Docs: api.md, setup.md, decisions.md (D-013).

### Tested
* 3 new tests (promotion works and is audited; only system_admin may change roles; 404/409/422 cases). 82 total passing.
* CLI script smoke-tested (create, then change role).

## 2026-10-16 · backend: foundation, voting core, simulated blockchain, tally

Branch: `feature/backend-blockchain`

### Changed
* **Fixed broken imports.** Models imported `app.database`, which didn't exist; the DB
  code was in a root `database/` folder. Moved it to `backend/app/database.py` and the
  model registry to `app/models/__init__.py`; removed `database/`.
* Removed committed `__pycache__/*.pyc`; `.gitignore` now covers Python caches, `.env`, `backend/data/`.
* **Auth is now database-backed** (the in-memory store lost everyone on restart): PBKDF2 passwords,
  hashed session tokens with expiry, logout, lockout, roles (`require_role`), rate-limited login.
* New tables: `auth_sessions`, `block_transactions`. Changed: `chain_blocks` (full block
  header), `ballots` (+`ballot_hash`), `receipts` (no user link, unique ballot hash),
  `voter_status` (WITHOUT ROWID), `elections` (key fingerprint, tally/publish fields).
  **Delete any old `voting.db`.**
* Elections, candidates, voter lists, close/tally/publish, audit log: `app/services/admin.py`, `app/api/admin.py`.
* Voting with atomic one-vote guarantee, AES-GCM ballot encryption and receipts: `app/services/voting.py`.
* **Simulated blockchain** (`app/blockchain/`): Merkle trees, PoW, multi-node majority
  consensus, mempool batching + shuffling, background sealer, audit/resync, tamper demo.
* Receipt verification with Merkle proofs; tally that refuses to count an untrusted chain; results block.
* Automatic close + tally after `closes_at`.
* Docs: `docs/blockchain.md`, `protocol.md`, `api.md`, `decisions.md`, `setup.md`, `backend/README.md`, `.env.example`.

### Tested
* 79 pytest tests (`cd backend && python -m pytest`), covering chain/merkle/network units,
  one-vote incl. 20 concurrent submissions, eligibility, voting window, ballot validation,
  receipts pending → confirmed with verifiable proof, tally with ties / invalid / zero-vote
  candidates, results block, privacy (no plaintext in DB/logs/chain files, no user link),
  append-only triggers, admin access control, tamper detection + resync, restart recovery.
* Manually ran the live server with the background sealer: seeded demo → 4 votes → receipt
  pending → confirmed → re-mined node detected → close → tally (4 ballots) → resync healthy.

### Not done / open
* **Frontend integration**: pages still use demo data (`verify-receipt.js`, `my-receipts.html`);
  `Frontend/data/api.json` is empty. Contract is in `docs/api.md`.
* No Alembic migrations yet (D-012). No load test (Q-3). No HTTPS config (deployment concern).
* Rate limiter is in-memory, per process.
* Open questions Q-1…Q-6 in `docs/decisions.md` (ties, abstaining, key custody, …).
