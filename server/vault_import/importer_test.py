# SPDX-License-Identifier: AGPL-3.0-or-later
"""The fixture vault into a real server through its API, and again: the second run changes nothing."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create
from vault_import.api import Api
from vault_import.importer import Importer
from vault_import.notes import read_vault

FIXTURE = Path(__file__).parent / "fixtures" / "vault"


@pytest.fixture(scope="module")
def server() -> TestClient:
    return TestClient(create())


@pytest.fixture(scope="module")
def api(server: TestClient) -> Api:
    user = create_user(server)
    return Api(server, {"Authorization": f"Bearer {user.jwt}"})


def _one(api: Api, kind: str, campaign: str, name: str) -> dict[str, Any]:
    [found] = [row for row in api.list(kind, campaign_id=campaign) if row["name"] == name]
    return found


def test_the_vault_imports_with_its_links_and_a_second_run_changes_nothing(api: Api) -> None:
    first = Importer(api, setting_slug="dnd").run(read_vault(FIXTURE))
    assert first.refused == [], first.refused
    assert len(first.created) == 13, first.created  # the campaign and twelve records
    assert first.skipped == [("Characters/Stray.md", "no campaign: and not setting_wide: true")]
    assert first.unresolved == {"Characters/Holst.md": ["Nobody Here"]}
    # The vault's own kind fields read as kinds; a word that isn't one is reported, never guessed.
    assert first.unread.get("Locations/The Fens.md") == ["location_type: warp-passage (not one of the location kinds)"]

    [campaign] = [row for row in api.list("campaign") if row["name"] == "The Split Antler"]
    dnd = next(row for row in api.list("setting") if row["slug"] == "dnd")
    assert campaign["setting_id"] == dnd["id"]
    # The campaign's provenance is its framing note's; a note's own is its record's (homebrew when none).
    assert (campaign["provenance"], campaign["source"]) == ("adapted", "The Lost Mine of Phandelver, Wizards of the Coast")
    framing = _one(api, "journal", campaign["id"], "The Split Antler — Framing")
    assert framing["kind"] == "campaign_framing"
    world = campaign["id"]
    fens, marsh, stable = (_one(api, "location", world, name) for name in ("The Fens", "Brindlemarsh", "Brindlemarsh Stable"))
    assert (marsh["parent_id"], stable["parent_id"], json.loads(marsh["aliases"])) == (fens["id"], marsh["id"], ["The Marsh Town"])
    mention = next(child for child in json.loads(marsh["entry"])[1]["children"] if child.get("type") == "mention")
    assert (mention["target_entity_id"], mention["children"]) == (stable["id"], [{"text": "stable"}])

    holst, dingus = _one(api, "person", world, "Holst"), _one(api, "person", world, "Dingus")
    assert holst["location_id"] == stable["id"]
    assert (json.loads(holst["keywords"]), json.loads(holst["voice"])["first_message"]) == (["stablemaster"], "Stalls are full.")
    properties = {row["key"]: row for row in api.properties("person", holst["id"])}
    assert (properties["Role"]["value"], properties["GM only"]["is_private"], properties["vault_path"]["value"]) == ("Stablemaster", True, "Characters/Holst.md")
    [disposition] = api.list("disposition", person_id=holst["id"])
    assert (disposition["target_person_id"], disposition["attitude"], disposition["note"]) == (dingus["id"], "wary", "Paid late once.")
    circle = _one(api, "faction", world, "Circle Compact")
    assert api.list("relationship", person_id=holst["id"], target_faction_id=circle["id"])[0]["kind"] == "member"

    quest, shard, ask = (_one(api, "hook", world, name) for name in ("Fix the Waystone", "Find the Shard", "Ask Holst"))
    assert api.list("hook_dependency", parent_hook_id=ask["id"], child_hook_id=shard["id"])
    assert api.list("hook_dependency", parent_hook_id=shard["id"], child_hook_id=quest["id"])
    assert shard["resolved_at"] is not None and quest["resolved_at"] is None

    item = _one(api, "item", world, "Waystone Shard")
    assert (stable["kind"], ask["kind"], item["kind"], fens["kind"]) == ("building", "side_quest", "misc", None)
    [holding] = api.list("entity_inventory", target_entity_type="person", target_entity_id=dingus["id"])
    instance, _etag = api.get("item_instance", holding["item_instance_id"])
    assert (instance["item_id"], instance["owner_person_id"], holding["quantity"]) == (item["id"], dingus["id"], 1)
    journal = _one(api, "journal", world, "Session 1 — Arrival")
    assert (journal["session_number"], journal["occurred_at"][:10]) == (1, "2026-11-01")
    assert (journal["provenance"], journal["source"]) == ("adapted", "The Lost Mine of Phandelver, Wizards of the Coast, ch. 1")
    assert (holst["provenance"], holst["source"]) == ("homebrew", None)

    second = Importer(api, setting_slug="dnd").run(read_vault(FIXTURE))
    assert (second.created, second.updated, second.refused) == ([], [], [])
    assert len(second.unchanged) == 12


def test_a_dry_run_writes_nothing(server: TestClient) -> None:
    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    report = Importer(api, setting_slug="dnd", dry_run=True).run(read_vault(FIXTURE))
    assert len(report.created) == 13
    assert [row for row in api.list("campaign") if row["name"] == "The Split Antler"] == []
