"""Zephyrex RPG Wiki: a consumer app built on the zephyrex server framework.

Worldbuilding and campaign wiki on the Zephyrex framework: entities, lore, secrets, timelines, maps, history.
All infrastructure (auth, DB, REST, GraphQL, migrations) comes from the
framework; this project only provides its own domain extensions.

    python rpg_wiki_app.py     # boot with uvicorn
    python -c "from rpg_wiki_app import create; create()"  # programmatic
"""
import os

os.environ.setdefault("APP_NAME", "Zephyrex RPG Wiki")
os.environ.setdefault("DATABASE_TYPE", "sqlite")
os.environ.setdefault("DATABASE_NAME", "zephyrex_rpg_wiki")
os.environ.setdefault("SEED_DATA", "true")
os.environ.setdefault("JWT_SECRET", "dev-only-change-in-production-32chars!")

from zephyrex import run

# auth_session (the framework's sign-in sessions: the hosted edition has accounts), genealogy (the
# framework's people), world_spatial (places), world_social (organisations), world_inventory
# (items, and what anyone carries) and rpg_core (worlds, and the
# character and campaign fields it adds to people and places). rpg_log stays in the repo but
# isn't loaded until its dependencies (rpg_core's successors rpg_traits, world_inventory) are
# in this repo; it depended on zephyrex-vtt's rpg_state (2026-11-20).
EXTENSIONS = "auth_session,genealogy,world_spatial,world_social,world_inventory,rpg_core"

if __name__ == "__main__":
    run(
        extensions=EXTENSIONS,
        extensions_path="./extensions",
        port=2000,
    )


def create():
    """Return a FastAPI app instance for testing or ASGI mounting."""
    from zephyrex import instance, set_extensions_root

    set_extensions_root("./extensions")
    return instance(extensions=EXTENSIONS)
