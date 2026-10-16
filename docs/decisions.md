# Decision Log

Every design decision, with the options we considered and why we chose this one
(README §8.1 "Decisions go in writing"). New decisions go at the bottom.
**Open questions** are at the end. Agents add questions there instead of guessing.

| ID | Date | Decision |
|---|---|---|
| D-001 | 2026-10-16 | Backend: FastAPI + SQLAlchemy 2 + SQLite |
| D-002 | 2026-10-16 | Blockchain is a **stdlib-only simulation** |
| D-003 | 2026-10-16 | Several simulated nodes with majority consensus; DB is a read copy |
| D-004 | 2026-10-16 | Batch + shuffle ballots into blocks |
| D-005 | 2026-10-16 | Receipt shown once; server stores only its hash; no user link |
| D-006 | 2026-10-16 | AES-256-GCM per-election key in a file outside the DB |
| D-007 | 2026-10-16 | Ties are reported, not broken automatically |
| D-008 | 2026-10-16 | Ballot = exactly one candidate for *every* position |
| D-009 | 2026-10-16 | Vote tables append-only via SQLite triggers |
| D-010 | 2026-10-16 | Auto close + tally at closing time; publishing is manual |
| D-011 | 2026-10-16 | Opaque DB-stored session tokens instead of JWT |
| D-012 | 2026-10-16 | No migration tool yet; `create_all` + triggers at startup |
| D-013 | 2026-10-16 | Admins are promoted by a system admin; first one via CLI |

---

### D-001 Backend stack
* **Chosen:** FastAPI, SQLAlchemy 2 ORM, SQLite (WAL mode, `BEGIN IMMEDIATE`).
* **Considered:** Flask; PostgreSQL from day one.
* **Why:** README §9 #1 suggests FastAPI. SQLite needs no server for a student
  project. `DATABASE_URL` can point to PostgreSQL later; the SQLite-specific bits
  (triggers, IMMEDIATE) are in `app/database.py`.

### D-002 Blockchain approach
* **Chosen:** our own Python simulation: hash-linked blocks, Merkle trees, toy PoW,
  simulated nodes. Only `hashlib`/`json`/`secrets`.
* **Considered:** Ethereum/Ganache smart contract; Hyperledger; a single hash-chain table.
* **Why:** project owner decision: "the blockchain is just supposed to be a
  simulation, not incorporate actual technologies". A single hash-chain table
  would be too thin to demonstrate tamper detection, so the simulation includes
  multiple nodes and consensus.

### D-003 Nodes and source of truth
* **Chosen:** `NODE_COUNT` (default 3) nodes, each with its own append-only JSONL
  files; commit on majority; the DB tables are an indexed copy; the tally requires
  majority = DB copy.
* **Why:** separate copies are what make one-sided tampering *detectable*. The DB
  copy keeps receipt lookups fast.

### D-004 Batching and shuffling
* **Chosen:** seal when `BLOCK_SIZE` (5) ballots are waiting or after
  `BLOCK_INTERVAL_SECONDS` (30), with a CSPRNG shuffle; force-seal on close.
* **Considered:** one block per vote (simplest).
* **Why:** one block per vote leaks timing; see protocol.md §4. The trade-off is a
  short "pending" period, which README §4 explicitly allows ("vote submit may show pending").

### D-005 Receipts
* **Chosen:** `VC-XXXX-XXXX-XXXX` (60 bits); store `sha256("receipt:"+code)` next to
  the ballot hash only. The code is returned once. "My Receipts" is client-side
  (browser storage / download).
* **Considered:** storing receipts per user so My Receipts could list them server-side.
* **Why:** that would link user → receipt → ballot, which breaks ballot privacy. Chosen by the project owner.

### D-006 Ballot encryption
* **Chosen:** AES-256-GCM (`cryptography` package), random 96-bit nonce, election
  id as associated data, random padding. One key per election in
  `ELECTION_KEYS_DIR/election_<id>.key` (chmod 600). Only its fingerprint is in the DB.
* **Considered:** Fernet (simpler API); homomorphic ElGamal; commit-reveal.
* **Why:** Fernet tokens contain a plaintext timestamp (a per-ballot time leak).
  Homomorphic tallying is a future upgrade (protocol.md §7). This is ordinary
  encryption, not "blockchain technology", so it fits D-002.

### D-007 Ties
* **Chosen:** results show `tie: true` and every tied candidate in `winner_ids`.
  The election admin resolves it under school rules (e.g. a run-off election).
* **Why:** the README asks us to "define tie handling". Silently picking a winner is
  worse than reporting a tie. *Needs confirmation from the student council (see Q-1).*

### D-008 Ballot shape
* **Chosen:** `{"position": candidate_id}`. Every position must be filled; no
  abstaining on a single position.
* **Why:** README §9 #5 "one candidate per position". Abstaining is an open question (Q-2).

### D-009 Append-only tables
* **Chosen:** SQLite `BEFORE UPDATE/DELETE` triggers on `ballots`, `voter_status`,
  `receipts`, `chain_blocks`, `block_transactions`, `audit_log`.
* **Why:** README §4: "Admins have no edit/delete vote function". Triggers enforce it
  even for code paths we didn't write.

### D-010 Automatic close and tally
* **Chosen:** the background loop closes and tallies any election past `closes_at`.
  Results are hidden until an election admin publishes them.
* **Why:** README §1 "votes are counted automatically"; §2 says admins publish results.

### D-011 Sessions
* **Chosen:** random bearer token; the DB stores sha256(token) with an expiry; logout deletes it.
* **Considered:** JWT.
* **Why:** easy to revoke, nothing to configure, and no signing secret to manage.

### D-012 Migrations
* **Chosen:** `Base.metadata.create_all()` + triggers on startup; no Alembic yet.
* **Why:** the schema is still changing. Add Alembic before the first real deployment.
  **Note:** if you have an old `voting.db` from before this change, delete it; the schema changed.

### D-013 Making admins
* **Chosen:** `/auth/register` only ever creates students. A `system_admin` promotes users with
  `PATCH /admin/users/{student_id}/role` (audited). The first system admin is bootstrapped with
  `python -m scripts.create_admin`, which needs shell access to the server. Nobody can change
  their own role, so the last system admin can't lock everyone out.
* **Considered:** a role field on registration; an "admin invite code".
* **Why:** a role field would let anyone make themselves an admin. Server shell access is
  already the root of trust, so bootstrapping from there adds no new attack surface.

---

## Open questions

| # | Question | Default until answered |
|---|---|---|
| Q-1 | How should ties be resolved (run-off, coin toss, council decides)? | Reported as a tie (D-007) |
| Q-2 | May a voter abstain on one position? | No: all positions required (D-008) |
| Q-3 | Expected number of voters (for load testing)? | Not load-tested yet |
| Q-4 | Who holds the election key files, and are they deleted after the results? | Stored on the server in `backend/data/keys` |
| Q-5 | School single sign-on later? | Student ID + password |
| Q-6 | How long is data kept after an election? | Not decided |
