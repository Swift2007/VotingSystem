# Backend

FastAPI + SQLAlchemy + SQLite, plus a **simulated blockchain** for tamper-evident vote recording.

* Getting started: [../docs/setup.md](../docs/setup.md)
* API contract: [../docs/api.md](../docs/api.md)
* How the chain works: [../docs/blockchain.md](../docs/blockchain.md)
* Privacy / receipts / tally design: [../docs/protocol.md](../docs/protocol.md)
* Why things are the way they are: [../docs/decisions.md](../docs/decisions.md)

```bash
pip install -r requirements.txt
python -m scripts.seed_demo          # optional demo data
uvicorn app.main:app --reload        # http://localhost:8000/docs
python -m pytest                     # tests
```

## Folder map

```
backend/
├── app/
│   ├── main.py            create_app(): DB init, chain service, background sealer/auto-tally, routers
│   ├── config.py          Settings from environment variables (see ../.env.example)
│   ├── database.py        engine, sessions, BEGIN IMMEDIATE, append-only triggers
│   ├── api/               HTTP routes, thin: auth, elections (+vote/results), receipts, admin, chain
│   ├── services/          business rules: auth, elections, admin, voting, receipts, tally
│   ├── models/            tables: user, admin (elections/results), candidate, student
│   │                      (eligibility/voter status/receipts), ballot, auditor (chain/audit log)
│   ├── schemas/           Pydantic request/response models
│   ├── crypto/            ballot.py (AES-GCM per-election keys), receipts.py (VC-codes)
│   ├── blockchain/        the simulation: hashing, merkle, block, pow, chain, mempool,
│   │                      node, network, service (see docs/blockchain.md)
│   └── core/              security (passwords/tokens), deps (auth/roles), audit, ratelimit, timeutil
├── scripts/
│   ├── seed_demo.py       demo users + an open election
│   ├── create_admin.py    CLI: create the first system_admin / change a role
│   ├── tamper_demo.py     CLI: status / tamper / resync a node
│   └── create_tables.py   create the schema without starting the server
├── tests/                 pytest suite (see tests/README.md)
├── migrations/            placeholder: no migration tool yet (decision D-012)
└── data/                  runtime data (git-ignored): voting.db, nodes/, keys/
```

## Rules the code follows (from README §8.3)

* Never log, store or return a plaintext vote choice, password, token or receipt code.
  `core/audit.py` refuses such fields.
* Never create a link between a voter and their choice (`tests/test_privacy.py` checks this).
* All checks run on the server (`core/deps.py::require_role`, `services/voting.py`).
* No secrets in code; configuration is via environment variables.
