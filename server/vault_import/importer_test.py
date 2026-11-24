# SPDX-License-Identifier: AGPL-3.0-or-later
"""The fixture vault into a real server through its API, and again: the second run changes nothing."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create

# The fixture vault's Holst.png is uploaded as his picture.
pytestmark = pytest.mark.usefixtures("memory_store")
from vault_import.api import Api
from vault_import.testing import setting_of
from vault_import.importer import Importer
from vault_import.notes import read_vault

FIXTURE = Path(__file__).parent / "fixtures" / "vault"


@pytest.fixture(scope="module")
def server() -> TestClient:
    return TestClient(create())


@pytest.fixture(scope="module")
def api(server: TestClient) -> Api:
    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    api.fantasy = setting_of(api, "fixture-fantasy")  # type: ignore[attr-defined]
    api.grimdark = setting_of(api, "fixture-grimdark")  # type: ignore[attr-defined]
    return api


def _one(api: Api, kind: str, campaign: str, name: str) -> dict[str, Any]:
    [found] = [row for row in api.list(kind, campaign_id=campaign) if row["name"] == name]
    return found


def test_the_vault_imports_with_its_links_and_a_second_run_changes_nothing(server: TestClient, api: Api) -> None:
    first = Importer(api, setting_slug=api.fantasy).run(read_vault(FIXTURE))
    assert first.refused == [], first.refused
    assert len(first.created) == 13, first.created  # the campaign and twelve records
    assert first.skipped == [
        ("Characters/Stray.md", "no campaign: and not setting_wide: true"),
        # The wiki alone serves no game systems (VTT's): its system: waits for a composed app.
        ("Lore/The Split Antler Framing.md", "its system and editions: this back end serves no game systems"),
    ]
    assert first.unresolved == {"Characters/Holst.md": ["Nobody Here"]}
    # The vault's own kind fields read as kinds; a word that isn't one is reported, never guessed.
    assert first.unread.get("Locations/The Fens.md") == ["location_type: warp-passage (not one of the location kinds)"]

    [campaign] = [row for row in api.list("campaign") if row["name"] == "The Split Antler"]
    dnd = next(row for row in api.list("setting") if row["slug"] == api.fantasy)
    assert campaign["setting_id"] == dnd["id"]
    # The campaign's provenance is its framing note's; a note's own is its record's (homebrew when none).
    assert (campaign["provenance"], campaign["source"]) == ("adapted", "The Lost Mine of Phandelver, Wizards of the Coast")
    assert campaign["is_scenario"] is True  # play starts a copy of it
    assert campaign["description"] == "A stable town at the edge of the fens."  # its framing note's
    framing = _one(api, "journal", campaign["id"], "The Split Antler — Framing")
    assert framing["kind"] == "campaign_framing"
    # Its framing note's tags are the campaign's play styles: shared ones matched, the rest its own.
    styles = {str(row["id"]): str(row["name"]) for row in api.list("taxon", kind="play_style")}
    links = api.list("entity_taxon", target_entity_type="campaign", target_entity_id=campaign["id"])
    tagged = sorted(styles[str(row["taxon_id"])] for row in links if str(row["taxon_id"]) in styles)
    assert tagged == ["combat-heavy", "mystery", "slow burn"]
    # Imported from a vault: scenario_repair's origin tag (a category), checked at the run's end.
    categories = {str(row["id"]): str(row["name"]) for row in api.list("taxon", kind="category")}
    assert [categories[str(row["taxon_id"])] for row in links if str(row["taxon_id"]) in categories] == ["Imported"]
    assert api.list("entity_taxon", target_entity_type="journal", target_entity_id=framing["id"]) == []
    world = campaign["id"]
    fens, marsh, stable = (_one(api, "location", world, name) for name in ("The Fens", "Brindlemarsh", "Brindlemarsh Stable"))
    assert (marsh["parent_id"], stable["parent_id"], json.loads(marsh["aliases"])) == (fens["id"], marsh["id"], ["The Marsh Town"])
    mention = next(child for child in json.loads(marsh["entry"])[1]["children"] if child.get("type") == "mention")
    assert (mention["target_entity_id"], mention["children"]) == (stable["id"], [{"text": "stable"}])

    holst, dingus = _one(api, "person", world, "Holst"), _one(api, "person", world, "Dingus")
    # A same-name image beside a note is the record's picture, as world_entities returns it.
    synced = {entity["name"]: entity for entity in server.get(f"/v1/world_entity?campaign_id={world}", headers=api.headers).json()["world_entities"]}
    assert synced["Holst"]["picture"] is not None and synced["Holst"]["picture"].startswith("/v1/asset/")
    # Or its image: by link, as it is.
    assert synced["Dingus"]["picture"] == "https://static.wikia.nocookie.net/forgottenrealms/images/d/d1/Halfling.png"
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

    second = Importer(api, setting_slug=api.fantasy).run(read_vault(FIXTURE))
    assert (second.created, second.updated, second.refused) == ([], [], [])
    assert len(second.unchanged) == 12


def test_a_dry_run_writes_nothing(server: TestClient) -> None:
    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    api.fantasy = setting_of(api, "fixture-fantasy")  # type: ignore[attr-defined]
    api.grimdark = setting_of(api, "fixture-grimdark")  # type: ignore[attr-defined]
    report = Importer(api, setting_slug=api.fantasy, dry_run=True).run(read_vault(FIXTURE))
    assert len(report.created) == 13
    assert [row for row in api.list("campaign") if row["name"] == "The Split Antler"] == []


def test_new_records_are_made_one_plural_create_a_kind(server: TestClient) -> None:
    """The operator: no one request per entity. Pass 1's new records go one plural create per kind."""

    class Counting(Api):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.singles: list[str] = []
            self.batches: list[tuple[str, int]] = []

        def create(self, resource: str, **fields: Any) -> dict[str, Any]:
            self.singles.append(resource)
            return super().create(resource, **fields)

        def create_many(self, resource: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
            self.batches.append((resource, len(rows)))
            return super().create_many(resource, rows)

    user = create_user(server)
    api = Counting(server, {"Authorization": f"Bearer {user.jwt}"})
    api.fantasy = setting_of(api, "fixture-fantasy")  # type: ignore[attr-defined]
    api.grimdark = setting_of(api, "fixture-grimdark")  # type: ignore[attr-defined]
    report = Importer(api, setting_slug=api.fantasy).run(read_vault(FIXTURE))
    assert report.refused == [], report.refused
    records = {"person", "location", "faction", "item", "journal", "hook"}
    kinds = [resource for resource, count in api.batches if count]
    # One plural create a kind (taxa and statuses have theirs too: batching_test).
    assert sorted(kinds) == sorted(set(kinds)) and sum(count for resource, count in api.batches if resource in records) == 12
    # No record of the six kinds is made alone (the campaign, its tags and links are their own calls).
    assert not {"person", "location", "faction", "item", "journal", "hook"} & set(api.singles)


def test_dh_campaign_types_read_as_the_contracts(server: TestClient, tmp_path: Path) -> None:
    """dh-campaign's own schema (its Templates/): character, quest, note and vehicle are a person, a
    hook, a journal and a vessel; a pregen with no kind is a PC; note_type gives a note's kind."""
    notes = {
        "OneShots/Ash/Ash Framing.md": "---\nentity_type: journal\nkind: campaign_framing\ncampaign: Ash Run\nname: Ash Run\n---\nThe frame.\n",
        "OneShots/Ash/Pregens/Vael.md": "---\nentity_type: character\ncampaign: Ash Run\nrole: Acolyte. Pregen, the Sage.\n---\nA sage.\n",
        "OneShots/Ash/Characters/Orrin.md": "---\nentity_type: character\nkind: npc\ncampaign: Ash Run\n---\nA clerk.\n",
        "OneShots/Ash/Quests/Find the Cell.md": "---\nentity_type: quest\nquest_type: side\ncampaign: Ash Run\n---\nFind it.\n",
        "OneShots/Ash/Notes/GM Notes.md": "---\nentity_type: note\nnote_type: gm-reference\ncampaign: Ash Run\n---\nSecrets.\n",
        "OneShots/Ash/Locations/The Pale Wake.md": "---\nentity_type: vehicle\nlocation_type: vessel\ncampaign: Ash Run\n---\nA frigate.\n",
    }
    for path, text in notes.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")
    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    api.fantasy = setting_of(api, "fixture-fantasy")  # type: ignore[attr-defined]
    api.grimdark = setting_of(api, "fixture-grimdark")  # type: ignore[attr-defined]
    report = Importer(api, setting_slug=api.fantasy).run(read_vault(tmp_path))
    assert report.skipped == [] and report.refused == [], (report.skipped, report.refused)
    assert not any("kind" in field or "_type" in field for fields in report.unread.values() for field in fields), report.unread
    [campaign] = [row for row in api.list("campaign") if row["name"] == "Ash Run"]
    kinds = {kind: {row["name"]: row.get("kind") for row in api.list(kind, campaign_id=campaign["id"])} for kind in ("person", "hook", "journal", "location")}
    assert kinds["person"] == {"Vael": "pc", "Orrin": "npc"}
    assert kinds["hook"] == {"Find the Cell": "side_quest"}
    assert kinds["journal"]["GM Notes"] == "note"
    assert kinds["location"] == {"The Pale Wake": "vessel"}


def test_a_plural_create_over_the_batch_limit_goes_in_chunks(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    """The framework takes at most 100 records a plural create; a vault's 430 people go in chunks."""
    from vault_import import api as api_module

    monkeypatch.setattr(api_module, "BATCH", 3)
    campaign = api.create("campaign", name="Chunked")
    made = api.create_many("person", [{"name": f"Crew {number}", "kind": "npc", "campaign_id": campaign["id"]} for number in range(7)])
    assert [row["name"] for row in made] == [f"Crew {number}" for number in range(7)]


def test_a_setting_pregen_note_is_a_listed_pregen_with_its_sheet(server: TestClient, tmp_path: Path) -> None:
    """Vault Author's setting-wide pregens (dh-campaign Setting/Pregens): vocabulary tags read as
    names, the role capitalised, type tags left out; the base64 build a private character sheet."""
    import base64

    build = {"homeworld": "voidborn", "role": "warrior", "characteristics": {"WS": 40, "BS": 35}, "wounds": 12}
    note = tmp_path / "Setting" / "Pregens" / "Dark Heresy 2e" / "Gerta Skaal.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\nentity_type: character\nkind: pc\nname: Gerta Skaal\nsetting_wide: true\nsystem: dark-heresy-2e\n"
        "role: Warrior (Feral World · Imperial Guard)\nprovenance: adapted\nsource: Dark Heresy 2e Core Rulebook pp.28–90\n"
        "tags: [character, pc, pregen, warrior, dark-heresy-2e]\n"
        f"initial_build: {base64.b64encode(json.dumps(build).encode()).decode()}\n"
        "canonical_sheet: {source: initial_build, advancements: [], items: []}\n---\n**A feral world warrior.**\n\nShe hunts.\n",
        encoding="utf-8",
    )
    user = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {user.jwt}"})
    api.fantasy = setting_of(api, "fixture-fantasy")  # type: ignore[attr-defined]
    api.grimdark = setting_of(api, "fixture-grimdark")  # type: ignore[attr-defined]
    report = Importer(api, setting_slug=api.grimdark).run(read_vault(tmp_path))
    assert report.refused == [] and report.skipped == [], (report.refused, report.skipped)
    assert not any(key.startswith(("initial_build", "canonical_sheet")) for keys in report.unread.values() for key in keys), report.unread
    [setting] = [one for one in api.list("setting") if one.get("slug") == api.grimdark]
    pregens = server.get(f"/v1/setting/{setting['id']}/pregen", headers={"Authorization": f"Bearer {user.jwt}"}).json()["pregens"]
    [gerta] = [one for one in pregens if one["name"] == "Gerta Skaal"]
    assert gerta["tags"] == ["Pregen", "Dark Heresy 2nd Edition", "Warrior"]
    sheets = {row["key"]: row for row in api.properties("person", gerta["id"])}
    assert json.loads(sheets["Character sheet"]["value"]) == build and sheets["Character sheet"]["is_private"] is True
    assert json.loads(sheets["Canonical sheet"]["value"])["source"] == "initial_build"
    # A career whose name the slug can't give back: the note's role names it.
    rt = tmp_path / "Setting" / "Pregens" / "Rogue Trader" / "Ione Sabre.md"
    rt.parent.mkdir(parents=True)
    rt.write_text(
        "---\nentity_type: character\nkind: pc\nname: Ione Sabre\nsetting_wide: true\nrole: Astropath Transcendent (Hive World)\n"
        f"tags: [character, pc, pregen, astropath-transcendent, rogue-trader]\ninitial_build: {base64.b64encode(json.dumps({'career': 'astropath'}).encode()).decode()}\n---\nShe listens.\n",
        encoding="utf-8",
    )
    Importer(api, setting_slug=api.grimdark).run(read_vault(tmp_path))
    pregens = server.get(f"/v1/setting/{setting['id']}/pregen", headers={"Authorization": f"Bearer {user.jwt}"}).json()["pregens"]
    assert [one["tags"] for one in pregens if one["name"] == "Ione Sabre"] == [["Pregen", "Astropath Transcendent", "Rogue Trader"]]
    dw = tmp_path / "Setting" / "Pregens" / "Deathwatch" / "Brother Castellan Varro.md"
    dw.parent.mkdir(parents=True)
    dw.write_text(
        "---\nentity_type: character\nkind: pc\nname: Brother Castellan Varro\nsetting_wide: true\nrole: Deathwatch Tactical Marine (Ultramarines)\n"
        "tags: [character, pc, pregen, tactical-marine, deathwatch]\n---\nHe holds the line.\n",
        encoding="utf-8",
    )
    Importer(api, setting_slug=api.grimdark).run(read_vault(tmp_path))
    pregens = server.get(f"/v1/setting/{setting['id']}/pregen", headers={"Authorization": f"Bearer {user.jwt}"}).json()["pregens"]
    assert [one["tags"] for one in pregens if one["name"] == "Brother Castellan Varro"] == [["Pregen", "Deathwatch", "Tactical Marine"]]


def test_a_scenario_left_unplayable_is_reported_loudly(api: Api, tmp_path: Path) -> None:
    """Sullenmire's shape: an opening that only points elsewhere, nothing to write one from, and no
    places. The import says so (and the command exits 1), instead of leaving a broken scenario."""
    (tmp_path / "Lore").mkdir()
    (tmp_path / "Characters").mkdir()
    (tmp_path / "Lore" / "Pointer Framing.md").write_text(
        "---\nentity_type: journal\nkind: campaign_framing\nname: Pointer Framing\ncampaign: Pointer Hold\n---\n"
        "## Opening Situation\n\nSee [[Pointer Briefing]]; the event graph is [[Pointer Quest]].\n",
        encoding="utf-8",
    )
    (tmp_path / "Characters" / "Kindless.md").write_text("---\nentity_type: character\nname: Kindless\ncampaign: Pointer Hold\n---\nA guard.\n", encoding="utf-8")
    report = Importer(api).run(read_vault(tmp_path))
    problems = report.unplayable["Pointer Hold"]
    # The person got a kind at import (an NPC); the opening and the places couldn't be mended.
    assert not any("no kind" in problem for problem in problems)
    assert any("only points elsewhere" in problem for problem in problems) and "no places" in problems
    assert "UNPLAYABLE Pointer Hold" in report.text(False)
    [held] = [row for row in api.list("person") if row["name"] == "Kindless"]
    assert held["kind"] == "npc"


def test_era_marks_canon_and_a_framing_marks_its_campaign(api: Api, tmp_path: Path) -> None:
    """Zephyrex RPG Settings' vaults: `era:` on a canon note (one or a list) and on a scenario's
    framing note become era taxa, so era scoping keeps other eras' canon out."""
    (tmp_path / "Lore").mkdir()
    (tmp_path / "Locations").mkdir()
    (tmp_path / "Locations" / "Gaslit Street.md").write_text(
        "---\nentity_type: location\nname: Gaslit Street\nkind: district\nsetting_wide: true\nera: Victorian\n---\nFog.\n", encoding="utf-8"
    )
    (tmp_path / "Locations" / "Long Bunker.md").write_text(
        "---\nentity_type: location\nname: Long Bunker\nkind: facility\nsetting_wide: true\nera: [World War II, Cold War]\n---\nConcrete.\n", encoding="utf-8"
    )
    (tmp_path / "Lore" / "Fog Hunt: Campaign Framing.md").write_text(
        "---\nentity_type: journal\nkind: campaign_framing\nname: \"Fog Hunt: Campaign Framing\"\ncampaign: Fog Hunt\nera: Victorian\n---\n"
        "## Opening Situation\n\nFog rolls off the river as a constable's whistle shrills on the Gaslit Street.\n",
        encoding="utf-8",
    )
    report = Importer(api, setting_slug=api.fantasy).run(read_vault(tmp_path))  # type: ignore[attr-defined]
    assert report.refused == [], report.refused
    eras = {str(row["id"]): str(row["name"]) for row in api.list("taxon", kind="era")}
    def eras_on(kind: str, record_id: str) -> set[str]:
        return {eras[str(row["taxon_id"])] for row in api.list("entity_taxon", target_entity_type=kind, target_entity_id=record_id) if str(row["taxon_id"]) in eras}
    [street] = [row for row in api.list("location") if row["name"] == "Gaslit Street"]
    [bunker] = [row for row in api.list("location") if row["name"] == "Long Bunker"]
    [hunt] = [row for row in api.list("campaign") if row["name"] == "Fog Hunt"]
    assert eras_on("location", street["id"]) == {"Victorian"} and eras_on("location", bunker["id"]) == {"World War II", "Cold War"}
    assert eras_on("campaign", hunt["id"]) == {"Victorian"}


def test_a_re_run_never_marks_a_playthrough_named_like_its_scenario(api: Api, tmp_path: Path) -> None:
    """Zephyrex RPG, 2026-11-24: a re-run matched campaigns by name and marked the operator's
    playthrough (named after its scenario) a scenario. A vault's campaigns are never playthroughs."""
    (tmp_path / "Characters").mkdir()
    (tmp_path / "Characters" / "Wick.md").write_text("---\nentity_type: person\nkind: npc\nname: Wick\ncampaign: Named Twice\n---\nA shepherd.\n", encoding="utf-8")
    first = Importer(api, setting_slug=api.fantasy).run(read_vault(tmp_path))  # type: ignore[attr-defined]
    assert first.refused == [], first.refused
    [scenario] = [row for row in api.list("campaign") if row["name"] == "Named Twice"]
    playthrough = api.create("campaign", name="Named Twice", scenario_id=scenario["id"])
    again = Importer(api, setting_slug=api.fantasy).run(read_vault(tmp_path))  # type: ignore[attr-defined]
    assert again.refused == [], again.refused
    held = {row["id"]: row for row in api.list("campaign") if row["name"] == "Named Twice"}
    assert held[scenario["id"]]["is_scenario"] is True
    assert not held[playthrough["id"]]["is_scenario"]


def test_a_re_run_writes_the_scenarios_own_record_beside_a_playthrough_that_has_the_change(api: Api, tmp_path: Path) -> None:
    """Zephyrex RPG, 2026-11-24: earlier runs wrote a pregen's new Description line onto the
    playthrough's copy (matched by name); a later run said the scenario's own PC was unchanged.
    Unchanged means the scenario's own record matches the note: it is written, and --force writes
    every matched record."""
    note = tmp_path / "Characters" / "Bryn.md"
    note.parent.mkdir()
    head = "---\nentity_type: person\nkind: pc\nname: Bryn\ncampaign: Copied Party\n---\n## Description\n\n"
    note.write_text(head + "A drover.\n", encoding="utf-8")
    assert Importer(api, setting_slug=api.fantasy).run(read_vault(tmp_path)).refused == []  # type: ignore[attr-defined]
    [scenario] = [row for row in api.list("campaign") if row["name"] == "Copied Party"]
    mine = _one(api, "person", scenario["id"], "Bryn")
    # The playthrough's copy already has the new line (as the misdirected runs left it).
    playthrough = api.create("campaign", name="Copied Party", scenario_id=scenario["id"])
    api.create("person", name="Bryn", kind="pc", campaign_id=playthrough["id"])
    note.write_text(head + "Level 1 Human Fighter. A drover.\n", encoding="utf-8")
    again = Importer(api, setting_slug=api.fantasy).run(read_vault(tmp_path))  # type: ignore[attr-defined]
    assert "person Bryn" in again.updated, again.text(False)
    held, _etag = api.get("person", mine["id"])
    assert "Level 1 Human Fighter" in str(held["entry"])
    # Nothing left to change: unchanged, unless forced.
    assert "person Bryn" in Importer(api, setting_slug=api.fantasy).run(read_vault(tmp_path)).unchanged  # type: ignore[attr-defined]
    forced = Importer(api, setting_slug=api.fantasy, force=True).run(read_vault(tmp_path))  # type: ignore[attr-defined]
    assert forced.refused == [], forced.refused
    assert "person Bryn" in forced.updated
