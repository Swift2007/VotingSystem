"""Merkle trees: the basis of verifiable receipts (README §3 "Receipt code and receipt verification")."""
import secrets

import pytest

from app.blockchain.merkle import merkle_proof, merkle_root, verify_proof


def txs(n: int) -> list[str]:
    return [secrets.token_hex(32) for _ in range(n)]


@pytest.mark.parametrize("n", [1, 2, 3, 5, 8, 100])
def test_every_leaf_has_a_valid_proof(n):
    """Every transaction can prove membership for trees of any size, including odd sizes."""
    leaves = txs(n)
    root = merkle_root(leaves)
    for i, leaf in enumerate(leaves):
        assert verify_proof(leaf, merkle_proof(leaves, i), root)


def test_root_depends_on_every_leaf_and_order():
    leaves = txs(4)
    root = merkle_root(leaves)
    assert merkle_root(list(reversed(leaves))) != root
    changed = leaves.copy()
    changed[2] = secrets.token_hex(32)
    assert merkle_root(changed) != root


def test_proof_fails_for_foreign_leaf_or_wrong_root():
    leaves = txs(5)
    proof = merkle_proof(leaves, 1)
    assert not verify_proof(secrets.token_hex(32), proof, merkle_root(leaves))
    assert not verify_proof(leaves[1], proof, merkle_root(txs(5)))


def test_single_leaf_root_is_not_the_raw_hash():
    """Domain separation: a leaf is hashed with a 0x00 prefix, so root != the tx itself."""
    leaf = txs(1)[0]
    assert merkle_root([leaf]) != leaf
    assert merkle_proof([leaf], 0) == []


def test_rejects_empty_tree_and_bad_input():
    with pytest.raises(ValueError):
        merkle_root([])
    with pytest.raises(ValueError):
        merkle_root(["not-a-hash"])
    assert not verify_proof("zz", [], "00")
