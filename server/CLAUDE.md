# Zephyrex RPG Wiki server

Consumer project built on the zephyrex server framework. Provides Zephyrex RPG Wiki’s domain extensions — the framework handles all infrastructure.

## Architecture

This is a **consumer project**, not a framework fork. It depends on `zephyrex[genealogy]` from the server-framework checkout beside the repository (`../../server-framework`, at the commit `deploy/frameworks.env` pins; `deploy/fetch-frameworks.sh` lays it out) and provides only domain-specific extensions:

- **genealogy** — people and their family trees (the framework's); rpg_core widens Person into the character table
- **world_spatial** — locations as a tree, at every scale (Tier 1: campaign-free)
- **rpg_core** — game systems and campaigns (worlds); injects `kind`, `campaign_id`, `user_id`, `location_id` and `entry` onto Person and `campaign_id` onto Location, so dependencies point one way, rpg_core → world_* (operator, 2026-11-20)
- **rpg_log** — session/event logging, kept in the repo but not loaded: it still depends on zephyrex-vtt's `rpg_state`, until its successors (rpg_traits, world_inventory) are here

Shared with the client: `../contract/wiki.json` (kinds and limits) and `../contract/*-cases.json` (rules both back ends compute).

## Commands

```bash
uv sync                      # Install from uv.lock (zephyrex from ../../server-framework)
.venv/bin/python rpg_wiki_app.py   # Boot the server on port 2000
.venv/bin/pytest extensions/ # Run extension tests
```

## How it works

`rpg_wiki_app.py` calls `zephyrex.run(extensions="auth_session,genealogy,world_spatial,rpg_core", extensions_path="./extensions")` (named so it never shadows the framework's own `zephyrex/app.py`). The framework:

1. Discovers `BLL_*.py` models in `./extensions/<name>/`
2. Auto-generates SQLAlchemy tables (via `create_all` fallback — no Alembic migrations needed for dev)
3. Auto-generates REST CRUD endpoints at `/v1/<resource>`
4. Auto-generates GraphQL schema
5. Provides core auth (User, Team, Role, Session) out of the box
