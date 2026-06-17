#!/usr/bin/env python3
"""Apply peer cards from a YAML spec to Honcho.

Reads peer-cards.yaml (gitignored — holds PII) and applies each peer's card via
`peer.set_card(list[str])`. `set_card` OVERWRITES the whole card, so the YAML is
the single source of truth: edit it and re-run to update.

Usage:
    export HONCHO_BASE_URL=http://localhost:8000
    python bootstrap_peer_cards.py peer-cards.yaml --dry-run   # preview
    python bootstrap_peer_cards.py peer-cards.yaml             # apply
"""

from __future__ import annotations

import argparse
import os
import sys

import yaml
from honcho import Honcho

DEFAULT_BASE_URL = "http://localhost:8000"
MAX_FACTS = 40  # Honcho peer-card cap.


def log(msg: str) -> None:
    print(msg, flush=True)


def load_spec(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "peers" not in data:
        raise ValueError(f"{path}: expected a top-level 'peers:' mapping")
    return data


def apply_cards(spec: dict, base_url: str, api_key: str | None, dry_run: bool) -> int:
    log(f"Honcho @ {base_url}  (dry_run={dry_run})")
    log("")

    for peer_id, entry in spec["peers"].items():
        workspace = entry.get("workspace")
        card = entry.get("card") or []
        if not workspace:
            raise ValueError(f"peer {peer_id!r}: missing 'workspace'")
        if not isinstance(card, list) or not all(isinstance(c, str) for c in card):
            raise ValueError(f"peer {peer_id!r}: 'card' must be a list of strings")
        if len(card) > MAX_FACTS:
            raise ValueError(
                f"peer {peer_id!r}: {len(card)} facts exceeds the {MAX_FACTS} cap"
            )

        targets = [workspace]
        if entry.get("also_seed_shared") and workspace != "shared":
            targets.append("shared")

        for ws in targets:
            log(f"peer {peer_id!r} in workspace {ws!r}: {len(card)} facts")
            if dry_run:
                for fact in card:
                    log(f"    + {fact}")
                log("    [would set_card]")
                continue
            client = Honcho(workspace_id=ws, base_url=base_url, api_key=api_key)
            peer = client.peer(peer_id)
            peer.set_card(card)
            got = peer.get_card() or []
            log(f"    ✓ card set ({len(got)} facts returned)")
        log("")

    log("dry-run complete — nothing written." if dry_run else "done.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", help="path to peer-cards.yaml")
    ap.add_argument(
        "--base-url",
        default=os.environ.get("HONCHO_BASE_URL", DEFAULT_BASE_URL),
        help="Honcho API base URL (env: HONCHO_BASE_URL)",
    )
    ap.add_argument("--dry-run", action="store_true", help="preview, write nothing")
    args = ap.parse_args()

    api_key = os.environ.get("HONCHO_API_KEY")
    try:
        spec = load_spec(args.spec)
        return apply_cards(spec, args.base_url, api_key, args.dry_run)
    except Exception as exc:
        log(f"ERROR: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
