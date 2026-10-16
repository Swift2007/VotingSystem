# Vote Protocol: Privacy, Receipts and Tally

> Status: **prototype design**. README §12: get this reviewed before any real election.
> Code: `backend/app/services/voting.py`, `receipts.py`, `tally.py`, `backend/app/crypto/`

This document explains how a vote travels through the system. At each step it
says **what is stored, where, and what it can be linked to**.

---

## 1. Data separation

| Table / file | Contains | Can be linked to a user? | Can be linked to a choice? |
|---|---|---|---|
| `users`, `auth_sessions` | identity, password hash, token hashes | yes | no |
| `eligible_voters` | (election, user) | yes | no |
| `voter_status` | (election, user) **who** voted | yes | no |
| `ballots` | random id, election, AES-GCM ciphertext, ballot hash | **no** (no user column, no timestamp, WITHOUT ROWID) | only with the election key |
| `receipts` | sha256(receipt code), ballot hash | **no** (no user column) | only through the ballot |
| `chain_blocks`, `block_transactions`, node `.jsonl` files | hashes only | no | no |
| `audit_log` | admin actions; `vote_cast` with **no actor** and only the election id | admin actions only | no |
| key files (`ELECTION_KEYS_DIR`) | one AES-256 key per election | no | decrypts ballots |

There is **no column anywhere** that joins a user to a ballot, a receipt or a
ballot hash. `tests/test_privacy.py` checks this.

## 2. Casting a vote

```
student ──POST /elections/{id}/vote {choices: {"President": 3, "Treasurer": 7}}──► API
```

1. **Checks** (server-side): signed in · role = student · election *open* by server
   clock · on the voter list · not already voted.
2. **Ballot validation**: exactly one candidate for every position, and each
   candidate belongs to that position in this election. Otherwise `400` and nothing is stored.
3. **Genesis** block ensured (anchors the election setup).
4. **One transaction** (`BEGIN IMMEDIATE`), all or nothing:
   * `INSERT voter_status(election, user)`. The primary key is the one-vote guard.
     A concurrent duplicate gets `409 Already voted`.
   * `ciphertext = nonce ‖ AES-256-GCM(key_e, {"choices": …, "pad": random}, aad=election_id)`
   * `ballot_id = random 128 bits`; `ballot_hash = sha256(ballot_id ‖ ciphertext)`
   * `INSERT ballots(ballot_id, election_id, ciphertext, ballot_hash)`
   * `code = "VC-XXXX-XXXX-XXXX"` (60 random bits); `INSERT receipts(sha256("receipt:"+code), election, ballot_hash)`
   * `INSERT audit_log(actor=NULL, "vote_cast", {election_id})`
5. **Mempool**: `ballot_hash` is queued for the next block.
6. **Response** (the only time the code is ever sent):
   `{receipt_code, ballot_hash, status: "pending", message}`.

The frontend should show the code with a copy button and may save it in the
browser (decision D-005). The server cannot show it again.

## 3. Receipts

* `POST /receipts/verify {code}` (POST so codes never appear in URLs or access logs; rate-limited).
* Unknown, malformed and mistyped codes all get the same "not found" answer.
* A valid code returns: election, `ballot_hash`, `status` (`pending` / `failed` / `confirmed`)
  and, once confirmed, the block and a Merkle proof ([blockchain.md §10](blockchain.md#10-verify-a-receipt-by-hand)).
* `counted: true` once the election has been tallied and the ballot was on the chain.
* It **never** returns the candidate. A receipt proves *inclusion*, not *content*.
  That is deliberate: a receipt that proved your choice could be used to buy or
  coerce votes.

## 4. Timing correlation

Even without a user column, someone watching the server could line up
"student X voted at 10:02:13" with "a ballot appeared at 10:02:13". Mitigations:

* `ballots` has no timestamp and no row order (`WITHOUT ROWID`, random primary key).
* `voter_status` is also `WITHOUT ROWID`.
* The `vote_cast` audit entry has no actor.
* AES-GCM is used instead of Fernet, because Fernet tokens embed the encryption time (D-006).
* Ballots are **batched** (`BLOCK_SIZE`, `BLOCK_INTERVAL_SECONDS`) and **shuffled**
  before sealing, so a block only says "one of these k ballots arrived in this window".

**Remaining risk:** an attacker with live access to the server process or the
database can still watch rows appear in real time. With very few voters,
batching helps little. Acceptable for a prototype; documented in §7.

## 5. Closing

* An election is closed when `now ≥ closes_at` **or** an admin pressed close
  (`elections.status = 'closed'`). `effective_status()` checks this on every request.
* `POST /admin/elections/{id}/close` (or the automatic background step after
  `closes_at`): ensures a genesis block exists, re-queues any stored-but-unsealed
  ballots, and force-seals the mempool.

## 6. Tally

`POST /admin/elections/{id}/tally` (also run automatically after `closes_at`):

1. Election closed and not yet tallied.
2. Close step (idempotent): everything sealed.
3. `trusted_chain()`: a majority of nodes hold the same valid chain, **and** the DB copy is identical. Otherwise `409`, no count.
4. Counted set = ballot hashes **on the chain**. If the ballot box and the chain
   disagree in either direction, `409`, no count.
5. Decrypt each ballot. A ballot that won't decrypt or doesn't match the candidate
   list counts as **invalid** (reported, never silently dropped).
6. Count. Candidates with zero votes are listed with `0`. **Ties are reported**
   (`tie: true`, several `winner_ids`) and not broken automatically (D-007).
7. Results document = `{election_id, total_ballots, invalid_ballots, counts, ballots}`, where
   `ballots` lists the valid decrypted ballots **sorted canonically** (so the order
   reveals nothing). `results_hash = sha256(canonical_json(document))`.
8. The results hash is appended as the final **`results` block**. The chain then accepts nothing more.
9. Results stay private until `POST /admin/elections/{id}/publish`. After that,
   `GET /elections/{id}/results` shows per-position counts, winners, ties, the
   results block, and the full results document, so **anyone can recount** and
   re-hash it.

## 7. Threat model (prototype)

| Threat | Covered? | How / why not |
|---|---|---|
| Double voting (incl. concurrent) | ✅ | `voter_status` PK inside an IMMEDIATE transaction |
| Voting outside the window / ineligible | ✅ | Server-side checks, re-checked inside the transaction |
| Admin edits or deletes a vote via the app | ✅ | No such function; append-only triggers |
| Silent edit of DB rows or one node's file | ✅ detected | Node majority + DB comparison; tally refuses |
| Changing candidates after opening | ✅ detected | Admin rule + genesis anchor |
| Results changed after tally | ✅ detected | Results hash in final block + published document |
| DB leak reveals votes | ✅ | Ballots encrypted; key outside DB |
| DB **and** key file leak | ❌ | Ballots can be decrypted (but still not linked to users) |
| Server operator watching in real time | ⚠️ partial | Batching/shuffling only; see §4 |
| Server operator rewrites all nodes and the DB | ❌ | All nodes are on one host (simulation). Upgrade path: separate hosts or public anchoring. |
| Brute-forcing receipt codes | ✅ | 60-bit codes + rate limit |
| Vote buying / coercion via receipt | ✅ | Receipt doesn't reveal the choice |

**Possible upgrades:** split the election key among several trustees (Shamir),
use homomorphic tallying so individual ballots are never decrypted, encrypt
in the browser so the server never sees the plaintext, and run the nodes on
separate machines.
