# Setup and Running

## 1. Install

```bash
cd VotingSystem
python3 -m venv .venv                     # skip if .venv already exists
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

Python 3.11+ is required (developed on 3.14).

## 2. Configure

```bash
cp .env.example .env      # then edit if needed
```

Every setting has a working default, so `.env` is optional for local development.
The app reads **environment variables** directly. To load `.env`, either run
`set -a; source .env; set +a` first, or use `uvicorn --env-file ../.env`.

By default, runtime data goes to `backend/data/` (git-ignored):

```
backend/data/
├── voting.db               SQLite database
├── nodes/node-1/election_1.jsonl   one chain copy per simulated node
├── nodes/node-2/…
└── keys/election_1.key     ballot encryption key (never commit, never share)
```

> If you have a `voting.db` from before the blockchain work, delete it. The schema
> changed and there is no migration tool yet (decision D-012).

## 3. Seed demo data (optional)

```bash
cd backend
python -m scripts.seed_demo
```

This creates `admin` (election_admin), `sysadmin`, `auditor`, and `student01` to `student10`,
all with password **`demo-password`**, plus an election that is open for 2 hours.

### Creating admin accounts yourself

Registration (`/auth/register`) always creates a **student**. To get staff accounts:

```bash
cd backend
python -m scripts.create_admin myname                   # first system_admin (asks for a password)
python -m scripts.create_admin someone election_admin   # or promote/create other roles
```

After that, a system admin can promote anyone who has registered, over HTTP:

```bash
curl -X PATCH $B/admin/users/student02/role -H "Authorization: Bearer $SYSADMIN_TOKEN" \
  -H 'Content-Type: application/json' -d '{"role":"election_admin"}'
```

## 4. Run the server

```bash
cd backend
uvicorn app.main:app --reload --env-file ../.env
```

* API docs (try every endpoint): http://localhost:8000/docs
* Health: http://localhost:8000/health

The frontend is served separately (e.g. VS Code Live Server on port 5500). Its
origin must be listed in `CORS_ORIGINS`.

## 5. Try the flow with curl

```bash
B=http://localhost:8000
TOKEN=$(curl -s -X POST $B/auth/login -H 'Content-Type: application/json' \
  -d '{"student_id":"student01","password":"demo-password"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s $B/elections/1/candidates
curl -s -X POST $B/elections/1/vote -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"choices":{"President":1,"Treasurer":3}}'
# → {"receipt_code":"VC-…","status":"pending",…}

curl -s -X POST $B/receipts/verify -H 'Content-Type: application/json' -d '{"code":"VC-…"}'
curl -s $B/chain/1/status
curl -s $B/chain/1/verify
```

Wait `BLOCK_INTERVAL_SECONDS`, or until `BLOCK_SIZE` ballots have been cast, and the
receipt status changes from `pending` to `confirmed`.

## 6. Tamper demo

```bash
export ENABLE_SIMULATION_TOOLS=true      # restart the server after setting this
python -m scripts.tamper_demo status 1
python -m scripts.tamper_demo tamper 1 node-2 1 edit
python -m scripts.tamper_demo status 1   # node-2 is BAD, majority still OK
python -m scripts.tamper_demo resync 1
```

Or use the HTTP endpoints described in [blockchain.md §11](blockchain.md#11-tamper-demo).

## 7. Tests

```bash
cd backend
python -m pytest              # whole suite (~10 s)
python -m pytest tests/blockchain -v
```

The tests use temporary directories, so they never touch `backend/data/`.

## 8. Backups

* Back up `backend/data/voting.db` and `backend/data/nodes/` together.
* Back up `backend/data/keys/` **separately and securely**. Anyone holding a key and
  the DB can read that election's ballots (but still can't link them to students).
* Never restore a backup *over* a running election's chain to "fix" it. Use
  `/chain/{id}/verify` and `/chain/{id}/resync` (README §4 Backups).
