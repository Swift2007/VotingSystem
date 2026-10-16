"""Simulated blockchain for the voting system.

This package is a teaching-scale *simulation* of a blockchain. It uses only
Python's standard library (hashlib, json, secrets) and no real blockchain
network or library (decision D-002 in docs/decisions.md).

Privacy boundary: this package only ever sees opaque hex hashes
(`ballot_hash`, genesis/results payload hashes). It never sees users,
candidates or vote choices (README critical requirement 3).

Layers, bottom-up (each module only imports the ones above it):

    hashing.py   canonical JSON + SHA-256 helpers
    merkle.py    Merkle root and inclusion proofs
    block.py     Block dataclass and block-hash rule
    pow.py       toy proof-of-work
    chain.py     genesis / next-block construction, block + chain validation
    mempool.py   ballots waiting to be sealed into a block
    node.py      one simulated validator node with its own chain files
    network.py   N nodes, majority consensus, audit, resync, tamper demo
    service.py   facade the rest of the app uses (talks to the database)

Full explanation: docs/blockchain.md
"""
