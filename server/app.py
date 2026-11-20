"""Zephyrex RPG Wiki: a consumer app built on the zephyrex server framework.

Worldbuilding and campaign wiki on the Zephyrex framework: entities, lore, secrets, timelines, maps, history.
All infrastructure (auth, DB, REST, GraphQL, migrations) comes from the
framework; this project only provides its own domain extensions.

    python app.py              # boot with uvicorn
    python -c "from app import create; create()"  # programmatic
"""
import os

os.environ.setdefault("APP_NAME", "Zephyrex RPG Wiki")
os.environ.setdefault("DATABASE_TYPE", "sqlite")
os.environ.setdefault("DATABASE_NAME", "zephyrex_rpg_wiki")
os.environ.setdefault("SEED_DATA", "true")
os.environ.setdefault("JWT_SECRET", "dev-only-change-in-production-32chars!")

from zephyrex import run

EXTENSIONS = "genealogy,rpg_log"

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
