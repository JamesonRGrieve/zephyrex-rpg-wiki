# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sullenmire's breakage (prod, 2026-11-22) mended through the API, and caught by validation."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create
from scenario_repair.repair import repair, validate
from scenario_repair.rules import briefing_text, is_pointer, opening_of, scenario_problems, start_place
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
