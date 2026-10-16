# Backend tests

Run from `backend/`:

```bash
../.venv/bin/python -m pytest          # everything
../.venv/bin/python -m pytest tests/blockchain   # just the chain simulation
```

| File | Covers (README reference) |
|---|---|
| `blockchain/test_merkle.py` | Merkle roots & inclusion proofs (receipt verification) |
| `blockchain/test_chain.py` | Block hashing, PoW, chain validation, tamper detection |
| `blockchain/test_network.py` | Node majority consensus, audit, resync, tamper modes |
| `blockchain/test_mempool.py` | Batching rules for sealing |
| `test_auth.py` | Sign-in, lockout, roles |
| `test_voting.py` | One-person-one-vote (incl. concurrency), eligibility, window, ballot validation |
| `test_receipts.py` | Receipt pending → confirmed with valid Merkle proof, no choice revealed |
| `test_tally.py` | Counting with ties, invalid ballots, zero-vote candidates; results block |
| `test_privacy.py` | No voter→choice link in DB, logs, chain files; append-only triggers |
| `test_admin_chain_api.py` | Admin access control, audit log, chain API, tamper demo |

Tests use a temporary SQLite file, temporary node/key directories, a
PoW difficulty of 1 and a fast password hash. The background sealer is
switched off so tests seal explicitly.
