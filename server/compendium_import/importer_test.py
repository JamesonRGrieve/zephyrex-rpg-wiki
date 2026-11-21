# SPDX-License-Identifier: AGPL-3.0-or-later
"""The SRD fixture (a few of dnd5e's pack files) into a real server as the dnd setting's canon, and
again: the second run changes nothing."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from compendium_import import dnd5e
from compendium_import.foundry import read_packs
from compendium_import.importer import COMPENDIUM_SOURCE, CompendiumImporter
from rpg_wiki_app import create
from vault_import.api import Api

FIXTURE = Path(__file__).parent / "fixtures" / "dnd5e"
PACKS = ["rules", "races", "spells", "spells24", "items", "monsters", "actors24"]


@pytest.fixture(scope="module")
def server() -> TestClient:
    return TestClient(create())


def _canon(api: Api, kind: str, setting_id: str) -> dict[str, dict[str, Any]]:
    return {str(row["name"]): row for row in api.list(kind, setting_id=setting_id) if not row.get("campaign_id")}


def test_the_srd_imports_as_canon_and_a_second_run_changes_nothing(server: TestClient) -> None:
    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    documents = read_packs(FIXTURE, PACKS)
    assert all(one.uuid.startswith("Compendium.dnd5e.") for one in documents)

    first = CompendiumImporter(api, "dnd").run(documents)
    assert first.refused == [], first.refused
    # The starter hero (a player character) stays out; everything else is made.
    assert [why for _path, why in first.skipped] == ["a starter hero (a player character, not canon)"]
    assert sorted(first.created) == sorted(
        [
            "journal Appendix A: Conditions",
            "journal Dragonborn",
            "journal Alarm",
            f"journal {dnd5e.ATTRIBUTION_NAME}",
            "item Adamantine Breastplate",
            "person Goblin",
            "person Goblin Warrior",
        ]
    )
    [setting] = [one for one in api.list("setting") if one.get("slug") == "dnd"]
    journals = _canon(api, "journal", setting["id"])
    alarm = journals["Alarm"]
    # One Alarm from both editions: the 2024 text first, the 2014 one beneath, both sources named.
    assert (alarm["provenance"], alarm["kind"], alarm["campaign_id"]) == ("official", "lore", None)
    assert dnd5e.SRD_521 in alarm["source"] and dnd5e.SRD_51 in alarm["source"]
    assert "SRD 5.1 (2014)" in alarm["entry"] and "@UUID" not in alarm["entry"] and "[[" not in alarm["entry"]
    assert "spell" in json.loads(alarm["keywords"])
    held = {row["key"]: row for row in api.properties("journal", str(alarm["id"]))}
    assert held[COMPENDIUM_SOURCE]["is_private"] is True and len(json.loads(held[COMPENDIUM_SOURCE]["value"])) == 2
    # Its category is a tag of the setting's.
    [spell] = [row for row in api.list("taxon", setting_id=setting["id"], kind="category") if row["name"] == "Spell"]
    assert [row["taxon_id"] for row in api.list("entity_taxon", target_entity_type="journal", target_entity_id=alarm["id"])] == [spell["id"]]
    # A creature: its features as its entry (lookups read as its name), its numbers private.
    people = _canon(api, "person", setting["id"])
    goblin = people["Goblin"]
    assert goblin["kind"] == "monster" and "Nimble Escape" in goblin["entry"] and "{monster}" not in goblin["entry"]
    stats = {row["key"]: row for row in api.properties("person", str(goblin["id"]))}
    assert json.loads(stats["Stat block (2014)"]["value"])["hp"] == 7
    assert _canon(api, "item", setting["id"])["Adamantine Breastplate"]["kind"] == "armour"
    assert "Creative Commons Attribution 4.0" in journals[dnd5e.ATTRIBUTION_NAME]["entry"]

    second = CompendiumImporter(api, "dnd").run(read_packs(FIXTURE, PACKS))
    assert (second.created, second.updated, second.refused) == ([], [], [])
    assert len(second.unchanged) == 7


def test_a_dry_run_writes_nothing(server: TestClient) -> None:
    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    report = CompendiumImporter(api, "dnd", dry_run=True).run(read_packs(FIXTURE, ["spells"]))
    assert report.created == ["journal Alarm", f"journal {dnd5e.ATTRIBUTION_NAME}"]
    [setting] = [one for one in api.list("setting") if one.get("slug") == "dnd"]
    assert "Alarm" not in _canon(api, "journal", setting["id"])


def test_the_40k_packs_import_raw_only_merged_across_lines(server: TestClient) -> None:
    from compendium_import import wh40k
    from compendium_import.importer import wh40k_system

    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    documents = wh40k.read_lines(Path(__file__).parent / "fixtures" / "wh40k")
    report = CompendiumImporter(api, "warhammer-40000", system=wh40k_system()).run(documents)
    assert report.refused == [], report.refused
    # A homebrew-only condition stays out: only the printed books come in.
    assert [why for _path, why in report.skipped] == ["no printed-book (raw) source"]
    assert sorted(report.created) == sorted(
        [
            "journal Resistance",
            "journal Feral World",
            "item Autocannon (Chimera Mount)",
            "location Bansidhe",
            "person Adeptus Arbites Arbitrator",
            "person Chimera Armoured Transport",
        ]
    )
    [setting] = [one for one in api.list("setting") if one.get("slug") == "warhammer-40000"]
    resistance = _canon(api, "journal", setting["id"])["Resistance"]
    # DH2's text first, Dark Heresy's beneath; every printed book named.
    assert "DH2: Core Rulebook, p. 131" in resistance["source"] and "DH: Core Rulebook, p. 122" in resistance["source"]
    assert "Dark Heresy" in resistance["entry"]
    assert _canon(api, "location", setting["id"])["Bansidhe"]["kind"] == "vessel"
    chimera = _canon(api, "person", setting["id"])["Chimera Armoured Transport"]
    assert (chimera["kind"], chimera["picture_url"]) == ("vehicle", "https://static.wikia.nocookie.net/warhammer40k/images/0/06/Chimera01.png")
    again = CompendiumImporter(api, "warhammer-40000", system=wh40k_system()).run(wh40k.read_lines(Path(__file__).parent / "fixtures" / "wh40k"))
    assert (again.created, again.updated) == ([], [])
