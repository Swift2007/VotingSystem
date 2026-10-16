"""A network of simulated nodes and its consensus rule.

Consensus (simplified, majority vote):
1. The proposer for height h is node[h % N] (round-robin). It is recorded
   in the block's `sealed_by` field.
2. Every node `check()`s the proposed block against its own chain.
3. If more than half accept, the block is *committed*: each accepting node
   appends it. Nodes that rejected are now out of sync until `resync()`.
4. Otherwise the proposal is dropped and `ConsensusError` is raised. The
   caller puts the ballots back into the mempool to retry.

Audit: every node validates its own file. The *canonical* chain is the one
held by a majority of nodes whose chains are valid and share a head hash.
Anything else (invalid, behind, or forked) is reported per node.
"""
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from app.blockchain.block import Block
from app.blockchain.chain import ValidationReport
from app.blockchain.errors import ConsensusError
from app.blockchain.node import SimNode


@dataclass
class ProposalResult:
    """Returned only for committed proposals (failures raise ConsensusError)."""
    block_hash: str
    accepted_by: list[str]
    rejected_by: dict[str, str]   # node id -> reason (these nodes are now out of sync)


@dataclass
class NodeAudit:
    node_id: str
    report: ValidationReport
    in_majority: bool

    def to_dict(self) -> dict:
        return {"node_id": self.node_id, "in_majority": self.in_majority, **self.report.to_dict()}


@dataclass
class NetworkAudit:
    election_id: int
    nodes: list[NodeAudit] = field(default_factory=list)
    canonical_head: str | None = None
    canonical_length: int = 0
    has_majority: bool = False

    @property
    def healthy(self) -> bool:
        return self.has_majority and all(n.in_majority for n in self.nodes)

    def to_dict(self) -> dict:
        return {
            "election_id": self.election_id,
            "healthy": self.healthy,
            "has_majority": self.has_majority,
            "canonical_head": self.canonical_head,
            "canonical_length": self.canonical_length,
            "nodes": [n.to_dict() for n in self.nodes],
        }


class SimNetwork:
    def __init__(self, data_dir: str | Path, node_count: int = 3) -> None:
        if node_count < 1:
            raise ValueError("node_count must be at least 1")
        self.nodes = [SimNode(f"node-{i + 1}", data_dir) for i in range(node_count)]

    @property
    def majority(self) -> int:
        return len(self.nodes) // 2 + 1

    def node(self, node_id: str) -> SimNode:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        raise KeyError(node_id)

    def proposer_for(self, height: int) -> SimNode:
        return self.nodes[height % len(self.nodes)]

    def propose(self, block: Block) -> ProposalResult:
        """Ask every node to check `block`; commit it if a majority accepts."""
        accepted: list[SimNode] = []
        rejected: dict[str, str] = {}
        for node in self.nodes:
            reason = node.check(block)
            if reason is None:
                accepted.append(node)
            else:
                rejected[node.node_id] = reason

        result = ProposalResult(block.block_hash, [n.node_id for n in accepted], rejected)
        if len(accepted) < self.majority:
            raise ConsensusError(
                f"block {block.height} accepted by {len(accepted)}/{len(self.nodes)} nodes; "
                f"need {self.majority}. Reasons: {rejected}"
            )
        for node in accepted:
            node.append(block)
        return result

    def audit(self, election_id: int) -> NetworkAudit:
        reports = {n.node_id: n.validate(election_id) for n in self.nodes}
        heads = Counter(
            (r.head_hash, r.length) for r in reports.values() if r.valid and r.length > 0
        )
        audit = NetworkAudit(election_id)
        if heads:
            (head, length), votes = heads.most_common(1)[0]
            if votes >= self.majority:
                audit.has_majority = True
                audit.canonical_head, audit.canonical_length = head, length
        elif all(r.valid and r.length == 0 for r in reports.values()):
            audit.has_majority = True  # nobody has a chain yet: trivially agreed

        for node_id, report in reports.items():
            in_majority = audit.has_majority and report.valid and (
                report.head_hash == audit.canonical_head and report.length == audit.canonical_length
            )
            audit.nodes.append(NodeAudit(node_id, report, in_majority))
        return audit

    def canonical_chain(self, election_id: int) -> list[Block] | None:
        """The majority chain, or None if there is no majority."""
        audit = self.audit(election_id)
        if not audit.has_majority:
            return None
        for node_audit in audit.nodes:
            if node_audit.in_majority:
                return self.node(node_audit.node_id).chain(election_id)
        return []

    def resync(self, election_id: int) -> list[str]:
        """Overwrite every out-of-majority node with the canonical chain."""
        audit = self.audit(election_id)
        canonical = self.canonical_chain(election_id)
        if canonical is None:
            raise ConsensusError("no majority chain to resync from")
        repaired = []
        for node_audit in audit.nodes:
            if not node_audit.in_majority:
                self.node(node_audit.node_id).replace_chain(election_id, canonical)
                repaired.append(node_audit.node_id)
        return repaired
