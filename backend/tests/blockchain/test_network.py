"""Simulated nodes + majority consensus (docs/blockchain.md "Network and consensus")."""
import secrets

import pytest

from app.blockchain.chain import build_block
from app.blockchain.errors import ConsensusError
from app.blockchain.network import SimNetwork


def h() -> str:
    return secrets.token_hex(32)


@pytest.fixture
def net(tmp_path):
    return SimNetwork(tmp_path, node_count=3)


def grow(net: SimNetwork, n_blocks: int, election_id: int = 7):
    prev = None
    for i in range(n_blocks):
        block = build_block(election_id=election_id, prev=prev, kind="genesis" if prev is None else "ballots",
                            transactions=[h()], difficulty=1, sealed_by=net.proposer_for(i).node_id)
        net.propose(block)
        prev = block
    return prev


def test_all_nodes_hold_identical_chains(net):
    head = grow(net, 4)
    audit = net.audit(7)
    assert audit.healthy and audit.canonical_head == head.block_hash and audit.canonical_length == 4
    assert {n.head(7).block_hash for n in net.nodes} == {head.block_hash}


def test_invalid_proposal_is_rejected_by_every_node(net):
    head = grow(net, 2)
    bad = build_block(election_id=7, prev=None, kind="genesis", transactions=[h()], difficulty=1, sealed_by="node-1")
    with pytest.raises(ConsensusError):
        net.propose(bad)  # a second genesis doesn't link to anyone's head
    assert net.audit(7).canonical_head == head.block_hash


@pytest.mark.parametrize("mode", ["edit", "remine", "drop"])
def test_tampered_minority_node_is_detected_and_resynced(net, mode):
    head = grow(net, 4)
    net.node("node-2").tamper(7, 1, mode)

    audit = net.audit(7)
    assert audit.has_majority and not audit.healthy
    bad = {n.node_id for n in audit.nodes if not n.in_majority}
    assert bad == {"node-2"}
    assert audit.canonical_head == head.block_hash  # the majority still holds the truth

    assert net.resync(7) == ["node-2"]
    assert net.audit(7).healthy


def test_consensus_survives_one_bad_node_but_flags_it(net):
    grow(net, 2)
    net.node("node-3").tamper(7, 1, "edit")
    prev = net.canonical_chain(7)[-1]
    block = build_block(election_id=7, prev=prev, kind="ballots", transactions=[h()], difficulty=1, sealed_by="node-1")
    result = net.propose(block)
    assert set(result.accepted_by) == {"node-1", "node-2"}
    assert "node-3" in result.rejected_by


def test_no_majority_means_no_commit(net):
    grow(net, 2)
    net.node("node-2").tamper(7, 1, "edit")
    net.node("node-3").tamper(7, 1, "edit")
    prev = net.node("node-1").head(7)
    block = build_block(election_id=7, prev=prev, kind="ballots", transactions=[h()], difficulty=1, sealed_by="node-1")
    with pytest.raises(ConsensusError):
        net.propose(block)
    assert net.canonical_chain(7) is None


def test_garbage_in_a_node_file_is_reported(net):
    grow(net, 2)
    with net.node("node-1").path(7).open("a") as fh:
        fh.write("{not json\n")
    audit = net.audit(7)
    node1 = next(n for n in audit.nodes if n.node_id == "node-1")
    assert not node1.report.valid and "unreadable" in node1.report.error
