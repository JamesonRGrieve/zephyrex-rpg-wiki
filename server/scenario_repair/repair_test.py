# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sullenmire's breakage (prod, 2026-11-22) mended through the API, and caught by validation."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create
from scenario_repair.repair import repair, validate
from scenario_repair.rules import briefing_text, is_framing_name, is_meta, is_pointer, mended_framing, unqualified_places, written_opening, opening_of, scenario_problems, start_place
from vault_import.api import Api

POINTER = "See Sullenmire — Player Briefing; the event graph is The Sullenmire Infiltration, and play-by-play is in Sullenmire — Run 1 Record."
DESCRIPTION = "An Inquisitor Lord steps off a civilian transport into a PDF processing yard on a hive world, unknown and unannounced."


def _p(*children: Any) -> dict[str, Any]:
    return {"type": "p", "children": list(children) or [{"text": ""}]}


def _h(level: int, text: str) -> dict[str, Any]:
    return {"type": f"h{level}", "children": [{"text": text}]}


def _mention(kind: str, record_id: str, text: str) -> dict[str, Any]:
    return {"type": "mention", "target_entity_type": kind, "target_entity_id": record_id, "children": [{"text": text}]}


def _framing(briefing_id: str) -> list[dict[str, Any]]:
    # Sullenmire's framing, as vault_import wrote it: the pointer's links are mentions.
    return [
        _h(1, "Sullenmire: Campaign Framing"),
        _h(2, "Premise"),
        _p({"text": "An Inquisitor Lord purges a genestealer cult from the officer corps."}),
        _h(2, "Opening Situation"),
        _p({"text": "See "}, _mention("journal", briefing_id, "Sullenmire — Player Briefing"), {"text": "; the event graph is The Sullenmire Infiltration, and play-by-play is in Sullenmire — Run 1 Record."}),
    ]


BRIEFING = [
    _h(1, "Sullenmire — Player Briefing"),
    _h(2, "Overview"),
    _p({"text": "Read or share this before play. A solo one-shot for one player."}),
    _h(2, "Who You Are"),
    _p({"text": "An Inquisitor Lord, the highest tier. Nobody at The Bastion knows you are here."}),
]


def test_the_rules_see_sullenmires_shape() -> None:
    assert is_pointer(POINTER) and is_pointer("") and not is_pointer(DESCRIPTION)
    assert is_framing_name("Sullenmire: Campaign Framing") and is_framing_name("The Split Antler — Framing") and not is_framing_name("Framing the Duke")
    assert is_pointer("Begin at the gate. Read the run sheet first.")  # names a run sheet
    assert briefing_text(BRIEFING) == "An Inquisitor Lord, the highest tier. Nobody at The Bastion knows you are here."
    found = opening_of(_framing("b"))
    assert found is not None and is_pointer(found[2], found[3])
    places = [{"id": "planet", "name": "Sullenmire"}, {"id": "bastion", "name": "The Bastion", "parent_id": "planet"}, {"id": "yard", "name": "Processing Yard", "parent_id": "planet"}]
    people = [{"id": "a", "location_id": "bastion"}, {"id": "b", "location_id": "bastion"}, {"id": "c", "location_id": "yard"}]
    # Named and most specific; a named world narrowed to where most people in it are; none named: the crowd.
    assert start_place("You arrive in the processing yard.", places, people)["id"] == "yard"  # type: ignore[index]
    assert start_place("Nobody on Sullenmire knows.", places, people)["id"] == "bastion"  # type: ignore[index]
    assert start_place("It begins.", places, people)["id"] == "bastion"  # type: ignore[index]
    assert scenario_problems([{"id": "x", "name": "Poul", "kind": None}], _framing("b"), []) == [
        "1 people have no kind: Poul",
        f"the Opening Situation only points elsewhere: {POINTER[:120]!r}",
        "no places",
    ]
    # A PC with no character sheet (where VTT serves sheets) is named first.
    assert scenario_problems([{"id": "d", "name": "Dex Calloran", "kind": "pc"}], _framing("b"), [{"id": "p"}], sheetless=["Dex Calloran"])[0] == "Dex Calloran has no character sheet"


@pytest.fixture(scope="module")
def api() -> Api:
    server = TestClient(create())
    user = create_user(server)
    return Api(server, {"Authorization": f"Bearer {user.jwt}"})


def test_sullenmire_is_mended_and_stays_mended(api: Api) -> None:
    scenario = api.create("campaign", name="Sullenmire", description=DESCRIPTION, is_scenario=True)
    planet = api.create("location", name="Sullenmire", kind="planet", campaign_id=scenario["id"])
    bastion = api.create("location", name="The Bastion", kind="building", campaign_id=scenario["id"], parent_id=planet["id"])
    poul = api.create("person", name="Poul", campaign_id=scenario["id"], location_id=bastion["id"])
    api.create("person", name="Commissar Aldren", campaign_id=scenario["id"], location_id=bastion["id"])
    briefing = api.create("journal", name="Sullenmire — Player Briefing", kind="note", campaign_id=scenario["id"], entry=BRIEFING)
    framing = api.create("journal", name="Sullenmire: Campaign Framing", kind="campaign_framing", campaign_id=scenario["id"], entry=_framing(briefing["id"]))
    play = api.create("campaign", name="Sullenmire — run", scenario_id=scenario["id"])
    seated = api.create("person", name="The Inquisitor", campaign_id=play["id"])
    extra = api.create("person", name="A bystander", campaign_id=play["id"])
    assert poul["kind"] is None and len(validate(api, scenario["id"])) == 2

    # The dry run reports and writes nothing.
    dry = {one.campaign_id: one for one in repair(api, dry_run=True, origins={"Sullenmire": "imported"}, seated={seated["id"]})}
    assert dry[scenario["id"]].kinds == {"npc": 2} and dry[scenario["id"]].origin == "Imported" and dry[scenario["id"]].problems_after == []
    assert dry[play["id"]].kinds == {"npc": 1, "pc": 1}
    assert api.get("person", poul["id"])[0]["kind"] is None

    done = {one.campaign_id: one for one in repair(api, dry_run=False, origins={"Sullenmire": "imported"}, seated={seated["id"]})}
    assert done[scenario["id"]].problems_after == [] and done[scenario["id"]].start == "The Bastion"
    assert [api.get("person", one["id"])[0]["kind"] for one in (poul, seated, extra)] == ["npc", "pc", "npc"]
    entry = api.get("journal", framing["id"])[0]["entry"]
    found = opening_of(entry if isinstance(entry, list) else __import__("json").loads(entry))
    assert found is not None and found[2].startswith(DESCRIPTION) and "Nobody at The Bastion" in found[2]
    text = __import__("json").dumps(entry)
    assert "Sources: " in text and "Starting Location" in text and bastion["id"] in text
    tags = {row["taxon_id"] for row in api.list("entity_taxon", target_entity_type="campaign", target_entity_id=scenario["id"])}
    assert {row["name"] for row in api.list("taxon", kind="category") if row["id"] in tags} == {"Imported"}
    assert [row["value"] for row in api.properties("campaign", scenario["id"]) if row["key"] == "Origin"] == ["transcript import"]

    # A second run finds nothing to do, and the framing stays as it is.
    again = {one.campaign_id: one for one in repair(api, dry_run=False, origins={"Sullenmire": "imported"})}
    assert again[scenario["id"]].kinds == {} and again[scenario["id"]].opening is None and again[scenario["id"]].start is None
    assert api.get("journal", framing["id"])[0]["entry"] == entry
    assert validate(api, scenario["id"]) == []


def test_it_loads_on_a_wiki_older_than_world_keys() -> None:
    """Prod's cd32e9e has no wiki_shared.WorldKeys: the rules load the same file by path."""
    import subprocess
    import sys
    from pathlib import Path

    code = (
        # As the app (or conftest) does: its extensions directory on zephyrex.extensions' path.
        "import sys, zephyrex.extensions as ext; ext.__path__ = ['extensions', *ext.__path__]\n"
        "sys.modules['zephyrex.extensions.wiki_shared.WorldKeys'] = None\n"
        "import scenario_repair.rules as rules\n"
        "assert rules.record_keys.__module__ == 'scenario_repair_world_keys', rules.record_keys.__module__\n"
        "print(sorted(rules.text_grams('Old Tam waves')))"
    )
    done = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert "'old tam'" in done.stdout


def test_the_commands_import_before_any_app_exists() -> None:
    """Zephyrex RPG on prod: zephyrex.extensions exists only once --app has made the app, so the
    commands' modules must import without it; the wiki's code is imported inside main."""
    import subprocess
    import sys
    from pathlib import Path

    code = (
        "import sys; sys.modules['zephyrex.extensions'] = None\n"
        "import scenario_repair.__main__, vault_import.__main__, book_import.__main__\n"
        "print('imported')"
    )
    done = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert "imported" in done.stdout


def test_a_framing_imported_as_lore_is_found_by_name_and_made_campaign_framing(api: Api) -> None:
    """Prod: framings imported before campaign_framing was a kind are lore ("Varek: Campaign Framing")."""
    scenario = api.create("campaign", name="Varek", description=DESCRIPTION, is_scenario=True)
    api.create("location", name="Varek Hive", kind="city", campaign_id=scenario["id"])
    framing = api.create("journal", name="Varek: Campaign Framing", kind="lore", campaign_id=scenario["id"],
                         entry=[_h(2, "Opening Situation"), _p({"text": "The lift doors open on the Varek Hive underdeck as the lumen-strips fail."})])
    assert any("is kind 'lore', not campaign_framing" in problem for problem in validate(api, scenario["id"]))
    [mended] = [one for one in repair(api, dry_run=False) if one.campaign_id == scenario["id"]]
    assert mended.framing_kind == "Varek: Campaign Framing" and mended.problems_after == []
    assert api.get("journal", framing["id"])[0]["kind"] == "campaign_framing"



def test_meta_paragraphs_never_open_a_scene() -> None:
    """Zephyrex RPG on prod: Sullenmire's opening read "Read or share this before play. A solo
    one-shot for one player." The opening takes only in-world text."""
    meta = "Read or share this before play. A solo one-shot for one player."
    assert is_meta(meta) and is_meta("This briefing is for the GM.") and not is_meta(DESCRIPTION)
    assert written_opening(meta, "") == ""
    assert written_opening(meta + "\n" + DESCRIPTION, briefing_text(BRIEFING)).startswith(DESCRIPTION)
    flagged = [{"type": "p", "children": [{"text": meta}]}]
    assert briefing_text([_h(2, "Who You Are"), *flagged, _p({"text": "An Inquisitor Lord, unknown and unannounced, steps off the transport."})]) == (
        "An Inquisitor Lord, unknown and unannounced, steps off the transport."
    )


def test_places_must_reach_a_planet_or_region() -> None:
    places = [
        {"id": "w", "name": "Sullenmire", "kind": "planet"},
        {"id": "b", "name": "The Bastion", "kind": "building", "parent_id": "w"},
        {"id": "y", "name": "Processing Yard", "kind": "facility"},
        {"id": "r", "name": "Yard Office", "kind": "room", "parent_id": "y"},
    ]
    assert unqualified_places(places) == ["Processing Yard (top: Processing Yard, facility)", "Yard Office (top: Processing Yard, facility)"]
    # Operator, 2026-11-23: a vessel in the void or the warp is fully qualified.
    ships = [{"id": "w", "name": "The Warp", "kind": "warp"}, {"id": "l", "name": "Penitent Lantern", "kind": "vessel", "parent_id": "w"}, {"id": "v", "name": "The Maw", "kind": "void"}]
    assert unqualified_places(ships) == []


def test_an_earlier_repairs_bad_opening_is_written_again(api: Api) -> None:
    scenario = api.create("campaign", name="Hive Desoleum", description="Read or share this before play. A solo one-shot for one player.", is_scenario=True)
    api.create("location", name="Desoleum", kind="planet", campaign_id=scenario["id"])
    briefing = api.create("journal", name="Hive Desoleum — Player Briefing", kind="note", campaign_id=scenario["id"], entry=BRIEFING)
    earlier = mended_framing(_framing(briefing["id"]), "Read or share this before play. A solo one-shot for one player.", None)
    framing = api.create("journal", name="Hive Desoleum: Campaign Framing", kind="campaign_framing", campaign_id=scenario["id"], entry=earlier)
    [dry] = [one for one in repair(api, dry_run=True) if one.campaign_id == scenario["id"]]
    assert dry.opening is not None and dry.opening.startswith("An Inquisitor Lord, the highest tier.") and "Read or share" not in dry.opening
    assert "opening written" in dry.line() and repr(dry.opening[:200]) in dry.line()
    [done] = [one for one in repair(api, dry_run=False) if one.campaign_id == scenario["id"]]
    found = opening_of(blocks_of_entry(api.get("journal", framing["id"])[0]["entry"]))
    assert found is not None and found[2].startswith("An Inquisitor Lord") and "Read or share" not in found[2] and done.problems_after == []
    [again] = [one for one in repair(api, dry_run=False) if one.campaign_id == scenario["id"]]
    assert again.opening is None and again.start is None


def blocks_of_entry(entry: Any) -> list[dict[str, Any]]:
    import json as jsonlib

    return entry if isinstance(entry, list) else jsonlib.loads(entry)



def test_a_scenario_with_no_framing_gets_one_from_what_it_already_says(api: Api) -> None:
    """Zephyrex RPG on prod: The Split Antler (made by hand, then imported) has no framing at all."""
    told = api.create("campaign", name="Split Antler Run", description="Rain hammers the fens as the party reaches Brindlemarsh Stable at dusk, mud to the knee.", is_scenario=True)
    api.create("location", name="Brindlemarsh Stable", kind="building", campaign_id=told["id"])
    silent = api.create("campaign", name="Silent Hold", is_scenario=True)
    api.create("location", name="Silent Keep", kind="building", campaign_id=silent["id"])
    dry = {one.campaign_id: one for one in repair(api, dry_run=True)}
    assert dry[told["id"]].framing_written == "Split Antler Run: Campaign Framing" and dry[told["id"]].problems_after == []
    assert "no campaign framing" in dry[silent["id"]].problems_after
    assert not [row for row in api.list("journal", campaign_id=told["id"]) if row["kind"] == "campaign_framing"]
    done = {one.campaign_id: one for one in repair(api, dry_run=False)}
    [framing] = [row for row in api.list("journal", campaign_id=told["id"]) if row["kind"] == "campaign_framing"]
    found = opening_of(blocks_of_entry(framing["entry"]))
    assert found is not None and found[2].startswith("Rain hammers the fens") and done[told["id"]].problems_after == []
    assert done[silent["id"]].framing_written is None and "no campaign framing" in done[silent["id"]].problems_after
    again = {one.campaign_id: one for one in repair(api, dry_run=False)}
    assert again[told["id"]].framing_written is None and again[told["id"]].opening is None
    assert len([row for row in api.list("journal", campaign_id=told["id"]) if row["kind"] == "campaign_framing"]) == 1
