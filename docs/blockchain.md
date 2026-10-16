# The Simulated Blockchain

> Code: [`backend/app/blockchain/`](../backend/app/blockchain/) · Tests: [`backend/tests/blockchain/`](../backend/tests/blockchain/)
> Related: [protocol.md](protocol.md) (privacy/receipt/tally design) · [decisions.md](decisions.md) · [api.md](api.md)

This is a **simulation** of a blockchain (decision D-002). It uses only Python's
standard library (`hashlib`, `json`, `secrets`) and does not connect to any real
blockchain network. It shows the ideas that make a blockchain
*tamper-evident* (hash links, Merkle trees, proof-of-work, several independent
copies, majority agreement) inside one backend process.

**Privacy boundary:** the chain only ever stores opaque SHA-256 hashes. It never
sees a student, a candidate or a vote choice.

---

## 1. The big picture

```
                    POST /elections/{id}/vote
                              │
             ┌────────────────▼─────────────────┐
             │ voting service (one DB txn)      │
             │  voter_status ← (election, user) │  ← one-vote guard
             │  ballots      ← AES-GCM blob     │  ← no user link
             │  receipts     ← sha256(code)     │
             └────────────────┬─────────────────┘
                              │ ballot_hash = sha256(ballot_id ‖ ciphertext)
                              ▼
                    ┌───────────────────┐
                    │      MEMPOOL      │  waits until BLOCK_SIZE ballots
                    │ (per election)    │  or BLOCK_INTERVAL_SECONDS
                    └─────────┬─────────┘
                              │ shuffle → Merkle root → mine (PoW)
                              ▼
          ┌─────────────── propose block ───────────────┐
          ▼                    ▼                        ▼
     ┌─────────┐          ┌─────────┐              ┌─────────┐
     │ node-1  │          │ node-2  │              │ node-3  │   each checks the block
     │ .jsonl  │          │ .jsonl  │              │ .jsonl  │   against ITS OWN copy
     └────┬────┘          └────┬────┘              └────┬────┘
          └──── majority (≥2 of 3) accept → commit ─────┘
                              │
                              ▼
                 DB read copy: chain_blocks + block_transactions
                 (indexed, used for receipts and the public API)
```

## 2. Files

| Module | What it does |
|---|---|
| `hashing.py` | `canonical_json()` (sorted keys, no spaces, UTF-8) and `sha256_hex()`. The one definition of "bytes to hash". |
| `merkle.py` | `merkle_root()`, `merkle_proof()`, `verify_proof()` |
| `block.py` | `Block` dataclass, `HEADER_FIELDS`, `compute_block_hash()` |
| `pow.py` | `mine()` and `meets_difficulty()` |
| `chain.py` | `build_block()`, `validate_block()`, `validate_chain()` (pure functions, no I/O) |
| `mempool.py` | Ballots waiting to be sealed, and when a seal is due |
| `node.py` | `SimNode`: one validator with its own append-only JSONL files, plus the tamper demo |
| `network.py` | `SimNetwork`: N nodes, `propose()`, `audit()`, `canonical_chain()`, `resync()` |
| `service.py` | `ChainService`: the only API the rest of the app uses. Connects chain ↔ database. |
| `errors.py` | `InvalidBlockError`, `ConsensusError`, `ChainIntegrityError`, `ChainFinalizedError` |

## 3. One chain per election

Each election has its own independent chain:

| Height | Kind | Transactions |
|---|---|---|
| 0 | `genesis` | 1: hash of the election's public setup (title, window, candidates, key fingerprint) |
| 1 … n | `ballots` | 1 … `BLOCK_SIZE` ballot hashes, **shuffled** |
| n + 1 | `results` | 1: hash of the results document. The chain is **final** after this. |

The genesis block is created when the first vote is cast (or when the election
closes, if nobody voted). The admin rules forbid changing candidates once an
election opens, and the genesis hash also records them. If someone edited the
`candidates` table directly, `election_params_hash()` would no longer match
block 0.

## 4. Block structure and hashing

```json
{
  "election_id": 2,
  "height": 1,
  "kind": "ballots",
  "timestamp": "2026-10-16T07:52:44Z",
  "prev_hash": "000c4e…(hash of block 0)",
  "merkle_root": "8f1a…",
  "tx_count": 3,
  "nonce": 2817,
  "difficulty": 3,
  "sealed_by": "node-2",
  "block_hash": "000a91…",
  "transactions": ["eb02…", "71c9…", "d3f0…"]
}
```

* **Header** = every field except `block_hash` and `transactions`.
* `block_hash = sha256(canonical_json(header))`.
* The header contains `merkle_root`, which is computed from `transactions`, so the
  hash commits to every transaction without including them directly.
* `timestamp` is rounded to whole seconds and is per *block*. No per-ballot time
  exists anywhere.

**Why it's tamper-evident:** change one character of a transaction → its Merkle
root changes → the block hash changes → the next block's `prev_hash` no longer
matches. Validation reports the exact height where the chain breaks.

## 5. Merkle trees

```
                 root = H(01 ‖ A ‖ B)
                 /                 \
       A = H(01 ‖ L0 ‖ L1)     B = H(01 ‖ L2 ‖ L2)   ← odd level: last node paired with itself
          /        \               /
   L0=H(00‖tx0) L1=H(00‖tx1)  L2=H(00‖tx2)
```

* Leaf: `sha256(0x00 ‖ tx)`; inner node: `sha256(0x01 ‖ left ‖ right)`.
  The prefixes ("domain separation") stop an attacker from passing an inner node
  off as a leaf.
* A **proof** for `tx1` is `[(L0, "L"), (B, "R")]`: the sibling at each level and
  which side it sits on. With 100 ballots in a block, a proof is only 7 hashes.

## 6. Proof-of-work

`mine()` tries `nonce = 0, 1, 2 …` until the block hash starts with
`difficulty` hex zeros (`POW_DIFFICULTY`, default 3, about 4,000 tries,
milliseconds). Each extra zero is ~16× more work.

In a real network PoW makes rewriting history expensive. Here it is
**illustrative**: all nodes run on one machine, so anyone with server access
could re-mine. What actually catches a rewrite is the majority of independent
copies (next section), plus anyone who wrote down a published block hash.

## 7. Network and consensus

* `NODE_COUNT` nodes (default 3), each storing
  `CHAIN_DATA_DIR/<node-id>/election_<id>.jsonl`, one block per line, append-only.
* **Proposer** for height *h* is `node[h % N]` (round-robin). It is recorded in `sealed_by`.
* **`propose(block)`**: each node runs `check()`:
  1. Its own file must parse and its own chain must be valid (a corrupt node doesn't vote).
  2. `validate_block(block, my_head, my_seen_transactions)` must pass.
* **Commit rule:** if at least ⌊N/2⌋+1 nodes accept, every accepting node appends the
  block. Nodes that rejected it are now out of sync (logged as a warning).
  Otherwise `ConsensusError` is raised and the ballots return to the mempool
  marked `failed`, to be retried.
* **`audit(election)`**: every node validates its own file. The *canonical chain* is
  the (head hash, length) shared by a majority of valid nodes. Each node is reported
  as `in_majority: true/false`, with `first_bad_height` and the error.
* **`resync(election)`** overwrites minority nodes with the canonical chain.

### Validation rules (`chain.validate_block`)

1. Kind is known; genesis only at height 0; nothing after a `results` block.
2. `height = prev.height + 1`, same `election_id`.
3. `prev_hash = prev.block_hash` (genesis: 64 zeros).
4. `block_hash` equals the recomputed header hash.
5. `block_hash` meets `difficulty`.
6. `tx_count = len(transactions) > 0` and `merkle_root` equals the recomputed root.
7. Every transaction is a SHA-256 hex digest and appears only **once in the whole chain**.
8. `timestamp ≥ prev.timestamp`.
9. Genesis and results blocks hold exactly one transaction.

## 8. Mempool and sealing

A ballot is not put in its own block. That would give it a unique position and
time that could be matched against when a student was seen voting (see
[protocol.md §4](protocol.md#4-timing-correlation)). Instead:

* Ballot hashes wait in the mempool for their election.
* The background loop (`app/main.py`, every `SEALER_TICK_SECONDS`) seals a block
  when **`BLOCK_SIZE`** ballots are waiting, **or** the oldest has waited
  **`BLOCK_INTERVAL_SECONDS`**.
* Before sealing, the batch is **shuffled** with a cryptographic RNG.
* Closing an election **force-seals** everything left.
* The mempool is in memory, but nothing is lost on restart: at startup,
  `restore_mempool()` re-queues every ballot in the database that isn't in a block yet.

Ballot status as reported to the voter:

| Status | Meaning |
|---|---|
| `pending` | Stored and encrypted; waiting for the next block |
| `failed` | The last seal attempt failed (no majority); it will be retried automatically |
| `confirmed` | In block *h*. The response includes the block hash and a Merkle proof. |

## 9. Database copy vs. node files

`chain_blocks` and `block_transactions` are an indexed copy for fast receipt
lookups and the public API. The **source of truth is the node majority**:

* `GET /chain/{id}/verify` reports each node *and* whether the DB copy matches the majority.
* At startup, `startup_check()` compares them and writes `chain_mismatch_at_startup`
  to the audit log if they differ.
* The tally uses `trusted_chain()`, which **refuses to count** unless the majority
  chain is valid *and* the DB copy is identical to it.
* SQLite triggers make both tables append-only (UPDATE/DELETE raise an error).
* Nothing ever "repairs" history from the database or a backup (README §4 Backups).

## 10. Verify a receipt by hand

`POST /receipts/verify {"code": "VC-AZ52-6H62-VTCE"}` returns something like:

```json
{
  "valid": true,
  "status": "confirmed",
  "ballot_hash": "eb0287ef…",
  "block": {"height": 2, "block_hash": "000b82…", "merkle_root": "de43c9…"},
  "merkle_proof": [["71c9…", "L"], ["a0f2…", "R"]]
}
```

Anyone can check it with nothing but Python:

```python
import hashlib

def verify(tx_hex, proof, root_hex):
    node = hashlib.sha256(b"\x00" + bytes.fromhex(tx_hex)).digest()
    for sibling_hex, side in proof:
        sib = bytes.fromhex(sibling_hex)
        pair = sib + node if side == "L" else node + sib
        node = hashlib.sha256(b"\x01" + pair).digest()
    return node.hex() == root_hex

print(verify(ballot_hash, merkle_proof, block["merkle_root"]))   # True
```

Then confirm the block is really on the chain: `GET /chain/{id}/blocks/{height}`
has the same `merkle_root`, and `GET /chain/{id}/verify` shows the nodes agree on
a head that this block leads to.

The receipt proves **inclusion**: your ballot is in the chain that gets counted.
It never reveals **which candidate** you picked.

## 11. Tamper demo

Turn it on with `ENABLE_SIMULATION_TOOLS=true` (never in a real election). Then, as a `system_admin`:

```bash
# corrupt node-2's copy of block 1 without re-mining
POST /chain/1/simulate/tamper   {"node_id": "node-2", "height": 1, "mode": "edit"}
GET  /chain/1/verify            # node-2: valid=false, first_bad_height=1; majority still healthy
POST /chain/1/resync            # node-2 overwritten from the majority → healthy again
```

| Mode | What it does | How it's caught |
|---|---|---|
| `edit` | Swaps one transaction, changes nothing else | The node's own validation fails (Merkle root mismatch) |
| `remine` | Swaps a transaction, recomputes the root, re-mines that block and all later ones | The node's chain is valid on its own, but its head differs from the majority |
| `drop` | Deletes the last block | The node is behind the majority |

The same demo is available from the command line, which works without the server:

```bash
cd backend
python -m scripts.tamper_demo status 1
python -m scripts.tamper_demo tamper 1 node-3 1 remine
python -m scripts.tamper_demo resync 1
```

Also try editing the database copy directly (e.g. with `sqlite3`, after
dropping a trigger). `/chain/1/verify` then reports `database_copy.matches_majority: false`
and the tally refuses to run.

## 12. Honest limits of the simulation

* All nodes live on one server under one operator. Majority consensus here shows
  the *mechanism*; it is not a defence against someone who controls the server.
  An upgrade path is to run nodes as separate processes or machines, or anchor
  head hashes on a public chain.
* PoW difficulty is tiny and only illustrative.
* The server sees the plaintext ballot briefly while encrypting it, and whoever
  holds the election key file can decrypt ballots (see [protocol.md](protocol.md)).
* If a block commits on the nodes but the DB write then fails (a crash at that
  exact moment), the DB copy falls behind. Startup and `/verify` report it;
  fixing it is a manual step.
