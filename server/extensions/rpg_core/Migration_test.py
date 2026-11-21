# SPDX-License-Identifier: AGPL-3.0-or-later
"""The wiki's migrations, run the way production runs them: the app boots on a fresh database
(conftest's temp DATABASE_PATH), the framework runs every extension's migrations, and genealogy's
persons table ends up with the columns rpg_core injects, as the others with theirs (operator,
2026-11-20: keep real FKs)."""

import glob
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rpg_wiki_app import create

INJECTED = {
    "persons": {"kind", "campaign_id", "user_id", "location_id", "entry"},
    "locations": {"campaign_id"},
    "factions": {"campaign_id"},
    "items": {"campaign_id"},
    "journals": {"campaign_id"},
    "hooks": {"campaign_id"},
    "taxons": {"campaign_id"},
    "statuses": {"campaign_id"},
    "relationships": {"faction_id", "target_faction_id", "colour", "mirror_relationship_id"},
}
FOREIGN_KEYS = {
    ("persons", "campaign_id"): "campaigns",
    ("persons", "location_id"): "locations",
    ("persons", "user_id"): "users",
    ("locations", "campaign_id"): "campaigns",
    ("locations", "associated_person_id"): "persons",
    ("items", "campaign_id"): "campaigns",
    ("journals", "campaign_id"): "campaigns",
    ("journals", "author_person_id"): "persons",
    ("hooks", "campaign_id"): "campaigns",
    ("hooks", "giver_person_id"): "persons",
    ("hooks", "giver_faction_id"): "factions",
    ("hook_dependencies", "parent_hook_id"): "hooks",
    ("hook_dependencies", "child_hook_id"): "hooks",
    ("person_hooks", "person_id"): "persons",
    ("person_hooks", "hook_id"): "hooks",
    ("faction_hooks", "faction_id"): "factions",
    ("faction_hooks", "hook_id"): "hooks",
    ("taxons", "campaign_id"): "campaigns",
    ("hooks", "resolved_journal_id"): "journals",
    ("dispositions", "person_id"): "persons",
    ("dispositions", "trigger_hook_id"): "hooks",
    ("relation_influences", "relationship_id"): "relationships",
    ("relation_influences", "hook_id"): "hooks",
    ("taxons", "parent_id"): "taxons",
    ("entity_taxons", "taxon_id"): "taxons",
    ("statuses", "campaign_id"): "campaigns",
    ("entity_statuses", "status_id"): "statuses",
    ("relationships", "faction_id"): "factions",
    ("relationships", "target_faction_id"): "factions",
    ("relationships", "mirror_relationship_id"): "relationships",
}


# The wiki's own extensions: each directory beside this one with a manifest (wiki_shared is a plain
# package; rpg_log stays in the repo, unloaded).
EXTENSIONS_ROOT = Path(__file__).parents[1]
OWN = sorted(path.parent.name for path in EXTENSIONS_ROOT.glob("*/manifest.toml") if path.parent.name != "rpg_log")
DECLARED: dict[str, dict[str, set[str]]] = {}


@pytest.fixture(scope="module")
def database() -> Iterator[sqlite3.Connection]:
    app = create()
    with TestClient(app):
        pass
    # Every table and column the wiki's models declare, by owning extension.
    for table in app.state.model_registry.database_manager.Base.metadata.sorted_tables:
        owner = table.info.get("extension")
        if owner in OWN:
            DECLARED.setdefault(owner, {})[table.name] = {column.name for column in table.columns}
    name = os.environ["DATABASE_NAME"]
    files = glob.glob(os.path.join(os.environ["DATABASE_PATH"], f"{name}*.db"))
    assert files, f"no database file for {name} in {os.environ['DATABASE_PATH']}"
    connection = sqlite3.connect(files[0])
    yield connection
    connection.close()


def test_the_injected_columns_are_on_their_tables(database: sqlite3.Connection) -> None:
    for table, columns in INJECTED.items():
        present = {row[1] for row in database.execute(f"PRAGMA table_info({table})")}
        assert columns <= present, (table, columns - present)


def test_the_injected_references_are_real_foreign_keys(database: sqlite3.Connection) -> None:
    for (table, column), target in FOREIGN_KEYS.items():
        keys = {(row[3], row[2]) for row in database.execute(f"PRAGMA foreign_key_list({table})")}
        assert (column, target) in keys, (table, column, target, keys)


def test_every_wiki_extension_ships_migrations() -> None:
    """The framework builds tables from the models only for an extension with no migration files at
    all (create_unmigrated_extension_tables), and soon refuses to boot outside tests when a table has
    none: every wiki extension has its own Alembic history."""
    missing = [name for name in OWN if not list((EXTENSIONS_ROOT / name / "migrations" / "versions").glob("*.py"))]
    assert not missing, f"extensions without migrations: {missing}"


def test_the_migrations_build_every_declared_table_and_column(database: sqlite3.Connection) -> None:
    """With migrations in every extension (above), no table comes from the models: so every table
    and column a wiki model declares (injected columns included) exists only if a migration made it."""
    assert DECLARED, "no wiki tables found in the models' metadata"
    gaps: list[str] = []
    for owner, tables in sorted(DECLARED.items()):
        for table, columns in sorted(tables.items()):
            present = {row[1] for row in database.execute(f"PRAGMA table_info({table})")}
            if not present:
                gaps.append(f"{owner}: no table {table}")
            elif columns - present:
                gaps.append(f"{owner}: {table} lacks {sorted(columns - present)}")
    assert not gaps, gaps


def test_each_extension_owns_its_tables(database: sqlite3.Connection) -> None:
    tables = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"campaigns", "locations", "factions", "items", "item_instances", "entity_inventories", "journals", "entity_posts", "hooks", "hook_dependencies", "person_hooks", "faction_hooks", "taxons", "entity_taxons", "statuses", "entity_statuses", "dispositions", "relation_influences"} <= tables


def test_hooks_002_keeps_a_create_all_table_and_adds_its_missing_columns() -> None:
    """vtt's rpg_state made ``hooks`` by create_all, without entry or giver_person_id: 002 keeps its
    rows and adds those columns, and creates only the tables that aren't there."""
    import importlib.util
    from pathlib import Path

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = Path(__file__).parents[1] / "world_narrative" / "migrations" / "versions" / "002_hooks.py"
    spec = importlib.util.spec_from_file_location("world_narrative_002_hooks", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE hooks (id VARCHAR PRIMARY KEY, name VARCHAR, kind VARCHAR, giver_faction_id VARCHAR, deleted_at DATETIME)"))
        connection.execute(sa.text("INSERT INTO hooks (id, name, kind) VALUES ('h1', 'Slay the wyrm', 'major_quest')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        inspector = sa.inspect(connection)
        assert {"entry", "giver_person_id"} <= {column["name"] for column in inspector.get_columns("hooks")}
        assert {"hook_dependencies", "person_hooks", "faction_hooks"} <= set(inspector.get_table_names())
        assert connection.execute(sa.text("SELECT name, kind FROM hooks")).all() == [("Slay the wyrm", "major_quest")]
