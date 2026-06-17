#!/usr/bin/env python3
"""Bootstrap Honcho workspaces + peers for the lean `tom` / `shared` topology.

Implements the entity layer from the "Peers & Workspace — Implementation Plan":
  - workspace `tom`    : peer `tom` (observe_me=true)
  - workspace `shared` : peer `tom` (observe_me=true)  [peer `wife` added later]

Idempotent: get-or-create everywhere, so re-running changes nothing. No personal
data lives here — peer-card content is separate (peer-cards.yaml, gitignored).

Usage (server auth is currently off, so no key needed):
    export HONCHO_BASE_URL=http://localhost:8000
    python bootstrap_entities.py --dry-run     # preview, writes nothing
    python bootstrap_entities.py               # apply
"""

from __future__ import annotations

import argparse
import os
import sys

from honcho import Honcho
from honcho.api_types import PeerConfig

DEFAULT_BASE_URL = "http://localhost:8000"

# --- Topology of record (lean start; `wife` is additive later) ----------------
# Each entry: workspace -> list of (peer_id, observe_me).
#   observe_me=True  -> Honcho builds a self-representation from this peer's msgs.
#   observe_me=False -> turns stored as session context but the peer is NOT modeled
#                       (correct for a querying assistant/bot peer).
TOPOLOGY: dict[str, list[tuple[str, bool]]] = {
    "tom": [
        ("tom", True),
    ],
    "shared": [
        ("tom", True),
        # --- wife end-state (uncomment when she onboards; see plan §3) ---------
        # ("wife", True),
    ],
    # --- wife's private workspace (additive later; see plan §3) ----------------
    # "wife": [
    #     ("wife", True),
    # ],
}

# Assistant/bot peer note (plan §4): do NOT pre-create the Hermes assistant peer
# — the Hermes Honcho plugin auto-creates its own. AFTER pointing Hermes at `tom`,
# find the auto-created assistant peer-id and set observe_me=False, e.g.:
#   client = Honcho(workspace_id="tom", base_url=...)
#   client.peer("<assistant-peer-id>", configuration=PeerConfig(observe_me=False))


def log(msg: str) -> None:
    print(msg, flush=True)


def bootstrap(base_url: str, api_key: str | None, dry_run: bool) -> int:
    log(f"Honcho @ {base_url}  (dry_run={dry_run})")
    log("")

    for workspace_id, peers in TOPOLOGY.items():
        log(f"workspace: {workspace_id}")
        client = Honcho(workspace_id=workspace_id, base_url=base_url, api_key=api_key)

        for peer_id, observe_me in peers:
            label = f"  peer {peer_id!r}  observe_me={observe_me}"
            if dry_run:
                log(f"{label}   [would get/create]")
                continue
            # peer(id, configuration=...) get-or-creates immediately with flags.
            client.peer(peer_id, configuration=PeerConfig(observe_me=observe_me))
            # Verify the flag landed.
            got = client.peer(peer_id).get_configuration()
            ok = getattr(got, "observe_me", None)
            log(f"{label}   ✓ (observe_me={ok})")
        log("")

    if dry_run:
        log("dry-run complete — nothing written.")
    else:
        log("done.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--base-url",
        default=os.environ.get("HONCHO_BASE_URL", DEFAULT_BASE_URL),
        help="Honcho API base URL (env: HONCHO_BASE_URL)",
    )
    ap.add_argument("--dry-run", action="store_true", help="preview, write nothing")
    args = ap.parse_args()

    # Auth is off on the local server; pass a key only if one is set.
    api_key = os.environ.get("HONCHO_API_KEY")

    try:
        return bootstrap(args.base_url, api_key, args.dry_run)
    except Exception as exc:  # surface a clean error, not a traceback wall
        log(f"ERROR: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
