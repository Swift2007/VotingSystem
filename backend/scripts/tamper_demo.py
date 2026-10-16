"""Command-line tamper demo for presentations. It works on the node files directly.

Run from backend/ (server may be running or not):

    python -m scripts.tamper_demo status  <election_id>
    python -m scripts.tamper_demo tamper  <election_id> <node-id> <height> [edit|remine|drop]
    python -m scripts.tamper_demo resync  <election_id>

`status` prints each node's validation result and whether it agrees with
the majority. See docs/blockchain.md, "Tamper demo".
"""
import sys

from app.blockchain.network import SimNetwork
from app.config import settings


def show(net: SimNetwork, election_id: int) -> None:
    audit = net.audit(election_id)
    print(f"election {election_id}: majority={'yes' if audit.has_majority else 'NO'} "
          f"length={audit.canonical_length} head={(audit.canonical_head or '-')[:16]}…")
    for n in audit.nodes:
        r = n.report
        mark = "OK " if n.in_majority else "BAD"
        print(f"  [{mark}] {n.node_id}: valid={r.valid} length={r.length} "
              f"head={(r.head_hash or '-')[:16]}… {r.error or ''}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    net = SimNetwork(settings.chain_data_dir, settings.node_count)
    command, election_id = argv[0], int(argv[1])
    if command == "status":
        show(net, election_id)
    elif command == "tamper":
        node_id, height = argv[2], int(argv[3])
        mode = argv[4] if len(argv) > 4 else "edit"
        print(net.node(node_id).tamper(election_id, height, mode))
        show(net, election_id)
    elif command == "resync":
        print("repaired:", net.resync(election_id))
        show(net, election_id)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
