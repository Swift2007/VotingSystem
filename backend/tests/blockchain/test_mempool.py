"""Batching rules: when a block gets sealed (docs/protocol.md "Timing correlation")."""
import time

from app.blockchain.mempool import Mempool


def test_due_when_block_size_reached():
    m = Mempool()
    for i in range(3):
        m.add(1, f"{i:064x}")
    assert m.due(block_size=3, interval_seconds=999) == [1]
    assert m.due(block_size=4, interval_seconds=999) == []


def test_due_after_interval():
    m = Mempool()
    m.add(1, "a" * 64)
    assert m.due(5, 999) == []
    time.sleep(0.02)
    assert m.due(5, 0.01) == [1]


def test_take_put_back_and_failed_state():
    m = Mempool()
    m.add(1, "a" * 64)
    m.add(1, "a" * 64)  # duplicate ignored
    m.add(1, "b" * 64)
    taken = m.take(1, 1)
    assert taken == ["a" * 64] and m.pending_count(1) == 1
    m.put_back(1, taken, "boom")
    assert m.state_of(1, "a" * 64) == "failed"
    assert m.state_of(1, "b" * 64) == "pending"
    assert m.last_error(1) == "boom"
    assert m.take(1, None) == ["a" * 64, "b" * 64] and m.pending_count(1) == 0
