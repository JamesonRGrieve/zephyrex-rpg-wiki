# Zephyrex RPG Wiki server

Consumer project built on the zephyrex server framework. Provides Zephyrex RPG Wiki’s domain extensions — the framework handles all infrastructure.

## Architecture

This is a **consumer project**, not a framework fork. It depends on `zephyrex[genealogy]` from the server-framework checkout beside the repository (`../../server-framework`, at the commit `deploy/frameworks.env` pins; `deploy/fetch-frameworks.sh` lays it out) and provides only domain-specific extensions:

- **genealogy** — person/family tree models for RPG characters (bundled in the framework)
- **rpg_log** — session/event logging for RPG campaigns (interim: needs zephyrex-vtt's `rpg_state`; see README)

## Commands

```bash
uv sync                      # Install from uv.lock (zephyrex from ../../server-framework)
.venv/bin/python app.py      # Boot the server on port 2000
.venv/bin/pytest extensions/ # Run extension tests
```

## How it works

`app.py` calls `zephyrex.run(extensions="genealogy,rpg_log", extensions_path="./extensions")`. The framework:

1. Discovers `BLL_*.py` models in `./extensions/<name>/`
2. Auto-generates SQLAlchemy tables (via `create_all` fallback — no Alembic migrations needed for dev)
3. Auto-generates REST CRUD endpoints at `/v1/<resource>`
4. Auto-generates GraphQL schema
5. Provides core auth (User, Team, Role, Session) out of the box
