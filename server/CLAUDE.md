# Zephyrex RPG Wiki server

Consumer project built on the zephyrex server framework. Provides Zephyrex RPG Wiki’s domain extensions — the framework handles all infrastructure.

## Architecture

This is a **consumer project**, not a framework fork. It depends on `zephyrex[genealogy]` from the server-framework checkout beside the repository (`../../server-framework`, at the commit `deploy/frameworks.env` pins; `deploy/fetch-frameworks.sh` lays it out) and provides only domain-specific extensions:

- **genealogy** — people and their relationships (the framework's); rpg_core widens Person into the character table, world_social widens Relationship (W5)
- **world_spatial** — places as a tree, at every scale; **world_social** — organisations as a tree, and organisation endpoints, colour and mirrors on relationships; **world_inventory** — items and what anyone carries; **world_narrative** — journals and the plot-hook DAG; **world_taxonomy** — tags, categories, races and statuses on any record (all Tier 1: campaign-free)
- **entity_posts** — posts on any record (Tier 0)
- **rpg_core** — campaigns (worlds; game systems are vtt's rpg_systems); injects `kind`, `campaign_id`, `user_id`, `location_id` and `entry` onto Person and `campaign_id` onto the world records, so dependencies point one way, rpg_core → world_* (operator, 2026-11-20); session reports and the world_entities sync for rpg-ai
- **rpg_log** — session/event logging, kept in the repo but not loaded: it still depends on zephyrex-vtt's `rpg_state`
- **wiki_shared** — a plain package (no manifest): the contract, the entry and summary rules, record checks

Each extension ships its own Alembic migrations (`migrations/versions`, Inspector-guarded); the fresh-database test is `extensions/rpg_core/Migration_test.py`.

Shared with the client: `../contract/wiki.json` (kinds and limits) and `../contract/*-cases.json` (rules both back ends compute).

## Commands

```bash
uv sync                      # Install from uv.lock (zephyrex from ../../server-framework)
.venv/bin/python rpg_wiki_app.py   # Boot the server on port 2000
.venv/bin/pytest extensions/ # Run extension tests
```

## How it works

`rpg_wiki_app.py` calls `zephyrex.run(extensions=EXTENSIONS, extensions_path="./extensions")` with the list above (named so it never shadows the framework's own `zephyrex/app.py`). The framework:

1. Discovers `BLL_*.py` models in `./extensions/<name>/`
2. Builds SQLAlchemy tables and runs each extension's migrations
3. Auto-generates REST CRUD endpoints at `/v1/<resource>`
4. Auto-generates GraphQL schema
5. Provides core auth (User, Team, Role, Session) out of the box
