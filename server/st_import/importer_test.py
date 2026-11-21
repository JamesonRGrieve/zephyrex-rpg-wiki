# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cards and World Info into a real server through its API, and again: the second run changes nothing."""

import json
from pathlib import Path
from typing import Any

import pytest

from fastapi.testclient import TestClient
from st_import.importer import StImporter
from st_import.sillytavern import read_card, read_world_info
from st_import.sillytavern_test import png_card
from vault_import.api import Api
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def store(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """The cloud extension's storage, kept in memory (its own tests cover its providers)."""
    from zephyrex.extensions.cloud.EXT_Cloud import EXT_Cloud

    files: dict[str, bytes] = {}

    async def upload_file(cls: Any, path: str, content: bytes, provider: Any = None) -> dict[str, Any]:
        files[path] = content
        return {"provider": "memory", "path": path}

    async def download_file(cls: Any, provider: str, path: str) -> bytes:
        return files[path]

    monkeypatch.setattr(EXT_Cloud, "upload_file", classmethod(upload_file))
    monkeypatch.setattr(EXT_Cloud, "download_file", classmethod(download_file))
    return files


def test_cards_and_world_info_import_and_a_second_run_changes_nothing(tmp_path: Path) -> None:
    server = TestClient(create())
    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    vel_png = tmp_path / "vel.png"
    vel_png.write_bytes(png_card(("ccv3", json.loads((FIXTURES / "vel.v3.json").read_text()))))
    cards = [read_card(FIXTURES / "holst.v2.json"), read_card(vel_png)]
    entries = read_world_info(FIXTURES / "waystones.world.json")

    first = StImporter(api, "The Split Antler", "dnd").import_all(cards, entries)
    assert first.refused == [], first.refused
    assert sorted(first.created) == sorted(
        ["campaign The Split Antler", "person Holst", "person Vel", "journal Holst's Stable", "journal The Waystones", "journal keeper"]
    )
    assert first.skipped == [(str(FIXTURES / "waystones.world.json") + "#2", "a disabled World Info entry")]

    [campaign] = [row for row in api.list("campaign") if row["name"] == "The Split Antler"]
    synced = {entity["name"]: entity for entity in server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=api.headers).json()["world_entities"]}
    holst, vel = synced["Holst"], synced["Vel"]
    assert (holst["voice"]["first_message"], holst["voice"]["examples"]) == ("Stalls are full, User.", ["Holst: No credit.", "Holst: Pay first."])
    assert vel["picture"] is not None and holst["picture"] is None
    waystones = synced["The Waystones"]
    assert (waystones["keywords"], waystones["lore"]["position"], waystones["lore"]["selective_logic"]) == (["waystone"], "at_depth", "not_any")
    assert synced["keeper"]["lore"]["always_active"] is True
    assert synced["Holst's Stable"]["lore"]["position"] == "after_character"
    properties = {row["key"]: row for row in api.properties("person", holst["id"])}
    assert (properties["Alternate greetings"]["value"], properties["Creator notes"]["is_private"]) == ("Back again?", True)

    second = StImporter(api, "The Split Antler", "dnd").import_all(cards, entries)
    assert (second.created, second.updated, second.refused) == ([], [], [])
    assert len(second.unchanged) == 5
