# peers-setup

One-time entity-layer bootstrap for the self-hosted Honcho server: workspaces,
peers, observe-flags, and peer cards. Implements the lean `tom` / `shared`
topology from the **Peers & Workspace — Implementation Plan**.

## ⚠️ Privacy

`peer-cards.yaml` contains **personal information** and is **gitignored** — it must
never be pushed to the public fork. Only the generic scripts in this folder are
committed. Keep card content local.

## Files

| File | Purpose |
|------|---------|
| `bootstrap_entities.py` | Get-or-create workspaces + peers with observe-flags (idempotent). |
| `peer-cards.yaml` | Peer-card facts (**gitignored, PII**). Source of truth for `set_card`. |
| `bootstrap_peer_cards.py` | Apply cards from the YAML (overwrites whole card; 40-fact cap). |

## Prerequisites

```bash
pip install honcho-ai pyyaml     # or: uv pip install honcho-ai pyyaml
```

Server auth is currently **off**, so no API key is needed when running against
`http://localhost:8000`. If auth is later enabled, set `HONCHO_API_KEY`.

## Run (on the M1 server, against the local Honcho)

```bash
export HONCHO_BASE_URL=http://localhost:8000

# 1. Preview — offline, writes nothing
python bootstrap_entities.py --dry-run
python bootstrap_peer_cards.py peer-cards.yaml --dry-run

# 2. Apply entities (idempotent — safe to re-run)
python bootstrap_entities.py

# 3. Apply Tom's card
python bootstrap_peer_cards.py peer-cards.yaml
```

## Topology

- **`tom`** — everything that is "just me" (personal + business, unified). peer `tom`, `observe_me=true`.
- **`shared`** — deliberately-shared "us" space. peer `tom` now; peer `wife` added later (one-line uncomment in `bootstrap_entities.py`).

The Hermes assistant peer is **not** pre-created here — the Hermes plugin
auto-creates it. After wiring Hermes to `tom`, set that auto-created peer's
`observe_me=false` (see the note in `bootstrap_entities.py`).

## Verify (plan §10)

1. `workspaces()` lists `tom` and `shared` — and nothing else.
2. peer `tom` exists in both, `observe_me=true`.
3. `tom`'s card returns the seeded facts.
4. Re-running both scripts changes nothing (idempotent).
5. Write ~1k tokens as `tom` in one session → after the deriver runs, `representation()` is non-empty.
