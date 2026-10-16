"""Blocks, proof-of-work and whole-chain validation (README critical req. 3, §3 "Blockchain recording")."""
import secrets
from dataclasses import replace

import pytest

from app.blockchain.block import Block
from app.blockchain.chain import ballot_transactions, build_block, find_transaction, validate_block, validate_chain
from app.blockchain.errors import InvalidBlockError
from app.blockchain.hashing import ZERO_HASH, canonical_json
from app.blockchain.merkle import merkle_root
from app.blockchain.pow import meets_difficulty, mine


def h() -> str:
    return secrets.token_hex(32)


def make_chain(ballot_blocks: int = 3, per_block: int = 2, difficulty: int = 2) -> list[Block]:
    genesis = build_block(election_id=1, prev=None, kind="genesis", transactions=[h()], difficulty=difficulty, sealed_by="node-1")
    blocks = [genesis]
    for _ in range(ballot_blocks):
        blocks.append(build_block(election_id=1, prev=blocks[-1], kind="ballots",
                                  transactions=[h() for _ in range(per_block)], difficulty=difficulty, sealed_by="node-2"))
    return blocks


def test_canonical_json_is_order_independent():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1}) == b'{"a":2,"b":1}'


def test_built_chain_is_valid_and_linked():
    blocks = make_chain()
    report = validate_chain(blocks)
    assert report.valid, report.error
    assert blocks[0].prev_hash == ZERO_HASH
    for prev, block in zip(blocks, blocks[1:]):
        assert block.prev_hash == prev.block_hash
        assert block.height == prev.height + 1
        assert meets_difficulty(block.block_hash, 2)


def test_block_hash_is_deterministic_and_roundtrips_through_dict():
    block = make_chain(1)[1]
    assert block.computed_hash() == block.block_hash
    assert Block.from_dict(block.to_dict()) == block


@pytest.mark.parametrize("field,value", [
    ("timestamp", "2099-01-01T00:00:00Z"),
    ("nonce", 999_999),
    ("sealed_by", "node-9"),
    ("tx_count", 7),
])
def test_editing_any_header_field_is_detected(field, value):
    blocks = make_chain()
    blocks[2] = replace(blocks[2], **{field: value})
    report = validate_chain(blocks)
    assert not report.valid
    assert report.first_bad_height == 2


def test_editing_a_transaction_breaks_the_merkle_root():
    blocks = make_chain()
    blocks[1] = replace(blocks[1], transactions=(h(),) + blocks[1].transactions[1:])
    report = validate_chain(blocks)
    assert not report.valid and report.first_bad_height == 1
    assert "merkle_root" in report.error


def test_remined_block_breaks_the_link_to_the_next_block():
    """Re-mining one edited block makes it valid alone, but the next block's prev_hash no longer matches."""
    blocks = make_chain()
    txs = (h(),) + blocks[1].transactions[1:]
    blocks[1] = mine(replace(blocks[1], transactions=txs, merkle_root=merkle_root(list(txs))))
    report = validate_chain(blocks)
    assert not report.valid and report.first_bad_height == 2
    assert "prev_hash" in report.error


def test_removing_or_reordering_blocks_is_detected():
    blocks = make_chain()
    assert not validate_chain(blocks[:1] + blocks[2:]).valid
    assert not validate_chain([blocks[0], blocks[2], blocks[1], blocks[3]]).valid


def test_same_ballot_cannot_be_recorded_twice():
    blocks = make_chain(1)
    dup = blocks[1].transactions[0]
    blocks.append(build_block(election_id=1, prev=blocks[-1], kind="ballots", transactions=[dup], difficulty=1, sealed_by="x"))
    report = validate_chain(blocks)
    assert not report.valid and "already recorded" in report.error


def test_genesis_rules_and_results_block_is_final():
    blocks = make_chain(1, difficulty=1)
    with pytest.raises(InvalidBlockError):
        validate_block(replace(blocks[1], kind="genesis"), blocks[0])
    results = build_block(election_id=1, prev=blocks[-1], kind="results", transactions=[h()], difficulty=1, sealed_by="x")
    after = build_block(election_id=1, prev=results, kind="ballots", transactions=[h()], difficulty=1, sealed_by="x")
    report = validate_chain(blocks + [results, after])
    assert not report.valid and "results block" in report.error


def test_pow_is_enforced():
    block = make_chain(0, difficulty=1)[0]
    weak = replace(block, difficulty=6)  # claims more work than was done
    weak = replace(weak, block_hash=weak.computed_hash())
    with pytest.raises(InvalidBlockError, match="proof-of-work"):
        validate_block(weak, None)


def test_helpers_find_ballots():
    blocks = make_chain(2, per_block=3)
    ballots = ballot_transactions(blocks)
    assert len(ballots) == 6 and blocks[0].transactions[0] not in ballots
    found = find_transaction(blocks, ballots[4])
    assert found and found[0].height == 2 and found[1] == 1


def test_empty_chain_is_valid():
    assert validate_chain([]).valid
