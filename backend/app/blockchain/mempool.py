"""The mempool: ballot hashes accepted by the app but not yet in a block.

Why batch ballots instead of one block per vote? With one ballot per block,
each ballot gets its own position and seal time, and those can be lined up
against "student X submitted at 10:02:13" (from logs or watching the
server). Batching several ballots, shuffling them and sealing them together
blurs that link (see docs/protocol.md, "Timing correlation").

Ballots are sealed when either:
* `block_size` ballots are waiting, or
* the oldest waiting ballot has waited `block_interval_seconds`, or
* the election closes (force seal).

The mempool is in memory, but nothing is lost on restart:
`ChainService.restore_mempool()` rebuilds it from ballots in the database
that have no block yet.

Only a time.monotonic() value per *election* is kept (when the queue became
non-empty), never a time per ballot.
"""
import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Queue:
    hashes: list[str] = field(default_factory=list)
    since: float | None = None      # monotonic time the queue became non-empty
    failed: set[str] = field(default_factory=set)  # hashes whose seal attempt failed
    last_error: str | None = None


class Mempool:
    def __init__(self) -> None:
        self._queues: dict[int, _Queue] = {}
        self._lock = threading.Lock()

    def _queue(self, election_id: int) -> _Queue:
        return self._queues.setdefault(election_id, _Queue())

    def add(self, election_id: int, tx_hash: str) -> None:
        """Queue one ballot hash (ignored if already queued)."""
        with self._lock:
            q = self._queue(election_id)
            if tx_hash in q.hashes:
                return
            if not q.hashes:
                q.since = time.monotonic()
            q.hashes.append(tx_hash)

    def take(self, election_id: int, limit: int | None) -> list[str]:
        """Remove and return up to `limit` hashes (all if None), oldest first."""
        with self._lock:
            q = self._queue(election_id)
            count = len(q.hashes) if limit is None else min(limit, len(q.hashes))
            taken, q.hashes = q.hashes[:count], q.hashes[count:]
            q.failed.difference_update(taken)
            q.since = time.monotonic() if q.hashes else None
            return taken

    def put_back(self, election_id: int, tx_hashes: list[str], error: str) -> None:
        """Return hashes after a failed seal; they are retried on the next tick."""
        with self._lock:
            q = self._queue(election_id)
            q.hashes = list(tx_hashes) + [h for h in q.hashes if h not in tx_hashes]
            q.failed.update(tx_hashes)
            q.last_error = error
            if q.since is None:
                q.since = time.monotonic()

    def due(self, block_size: int, interval_seconds: float) -> list[int]:
        """Election ids whose queue should be sealed now."""
        now = time.monotonic()
        with self._lock:
            return [
                eid for eid, q in self._queues.items()
                if q.hashes and (
                    len(q.hashes) >= block_size
                    or (q.since is not None and now - q.since >= interval_seconds)
                )
            ]

    def pending_count(self, election_id: int) -> int:
        with self._lock:
            return len(self._queue(election_id).hashes)

    def state_of(self, election_id: int, tx_hash: str) -> str | None:
        """'pending', 'failed' (last seal attempt failed, will retry) or None."""
        with self._lock:
            q = self._queue(election_id)
            if tx_hash not in q.hashes:
                return None
            return "failed" if tx_hash in q.failed else "pending"

    def last_error(self, election_id: int) -> str | None:
        with self._lock:
            return self._queue(election_id).last_error
