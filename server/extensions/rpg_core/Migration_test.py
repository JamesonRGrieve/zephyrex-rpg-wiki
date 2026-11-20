# SPDX-License-Identifier: AGPL-3.0-or-later
"""The wiki's migrations, run the way production runs them: the app boots on a fresh database
(conftest's temp DATABASE_PATH), the framework runs every extension's migrations, and genealogy's
persons table ends up with the columns rpg_core injects, as the others with theirs (operator,
2026-11-20: keep real FKs)."""

import glob
import os
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from rpg_wiki_app import create

INJECTED = {
    "persons": {"kind", "campaign_id", "user_id", "location_id", "entry"},
    "locations": {"campaign_id"},
    "factions": {"campaign_id"},
    "items": {"campaign_id"},
}
FOREIGN_KEYS = {
    ("persons", "campaign_id"): "campaigns",
    ("persons", "location_id"): "locations",
    ("persons", "user_id"): "users",
    ("locations", "campaign_id"): "campaigns",
    ("locations", "associated_person_id"): "persons",
    ("items", "campaign_id"): "campaigns",
}


@pytest.fixture(scope="module")
def database() -> Iterator[sqlite3.Connection]:
    with TestClient(create()):
        pass
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


def test_each_extension_owns_its_tables(database: sqlite3.Connection) -> None:
    tables = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"campaigns", "locations", "factions", "items", "item_instances", "entity_inventories"} <= tables
