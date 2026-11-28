# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core and world_spatial against a real server, the same rules as the lite edition's
(client/src/app/api/v1/routes.test.ts): a world, places in a tree with kinds from the contract and
no cycles, people with a kind, a world and a place, entries kept with their plain text, and one
person's records invisible to another."""

import json
from collections.abc import Iterator
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create

ENTRY = [{"type": "p", "children": [{"text": "A port city."}]}]


@pytest.fixture(scope="module")
def server() -> Iterator[TestClient]:
    yield TestClient(create())


@pytest.fixture(scope="module")
def person(server: TestClient) -> Any:
    return create_user(server)


@pytest.fixture(scope="module")
def other(server: TestClient) -> Any:
    return create_user(server)


def _headers(user: Any, **extra: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user.jwt}", **extra}


def _create(server: TestClient, user: Any, resource: str, **fields: Any) -> dict[str, Any]:
    response = server.post(f"/v1/{resource}", json={resource: fields}, headers=_headers(user))
    assert response.status_code == 201, response.text
    record: dict[str, Any] = response.json()[resource]
    return record


def _put(server: TestClient, user: Any, resource: str, record: dict[str, Any], **fields: Any) -> Any:
    current = server.get(f"/v1/{resource}/{record['id']}", headers=_headers(user))
    return server.put(
        f"/v1/{resource}/{record['id']}",
        json={resource: fields},
        headers=_headers(user, **{"If-Match": current.headers["ETag"]}),
    )


@pytest.fixture(scope="module")
def world(server: TestClient, person: Any) -> dict[str, Any]:
    return _create(server, person, "campaign", name="The Salt Coast")


class TestPlaces:
    def test_a_place_keeps_its_entry_and_plain_text(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        port = _create(server, person, "location", name="Saltmarsh", kind="city", entry=ENTRY, campaign_id=world["id"])
        assert json.loads(port["entry"]) == ENTRY
        assert port["description"] == "A port city."
        assert port["campaign_id"] == world["id"]

    def test_a_kind_outside_the_contract_is_refused(self, server: TestClient, person: Any) -> None:
        response = server.post("/v1/location", json={"location": {"name": "Nowhere", "kind": "galaxy"}}, headers=_headers(person))
        assert response.status_code == 422, response.text

    def test_a_blank_name_is_refused(self, server: TestClient, person: Any) -> None:
        response = server.post("/v1/location", json={"location": {"name": "   "}}, headers=_headers(person))
        assert response.status_code == 422, response.text

    def test_an_entry_out_of_shape_is_refused(self, server: TestClient, person: Any) -> None:
        response = server.post("/v1/location", json={"location": {"name": "Odd", "entry": {"type": "p"}}}, headers=_headers(person))
        assert response.status_code == 422, response.text

    def test_places_nest_but_never_in_a_cycle(self, server: TestClient, person: Any) -> None:
        region = _create(server, person, "location", name="The Coast", kind="region")
        city = _create(server, person, "location", name="Brine", kind="city", parent_id=region["id"])
        assert city["parent_id"] == region["id"]
        response = _put(server, person, "location", region, parent_id=city["id"])
        assert response.status_code == 422, response.text
        response = _put(server, person, "location", region, parent_id=region["id"])
        assert response.status_code == 422, response.text


class TestPeople:
    def test_a_person_has_a_kind_a_world_a_place_and_an_entry(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        inn = _create(server, person, "location", name="The Gull", kind="building")
        mira = _create(
            server, person, "person", name="Mira", kind="npc", campaign_id=world["id"], location_id=inn["id"], entry=ENTRY
        )
        assert (mira["kind"], mira["campaign_id"], mira["location_id"]) == ("npc", world["id"], inn["id"])
        assert mira["description"] == "A port city."

    def test_people_list_under_persons(self, server: TestClient, person: Any) -> None:
        # The list key the lite twin answers with (client/src/lib/worldRecords.ts).
        assert "persons" in server.get("/v1/person", headers=_headers(person)).json()

    def test_a_person_kind_outside_the_contract_is_refused(self, server: TestClient, person: Any) -> None:
        response = server.post("/v1/person", json={"person": {"name": "Odd", "kind": "dragon"}}, headers=_headers(person))
        assert response.status_code == 422, response.text


class TestWorlds:
    def test_one_persons_world_is_not_anothers(self, server: TestClient, person: Any, other: Any, world: dict[str, Any]) -> None:
        assert server.get(f"/v1/campaign/{world['id']}", headers=_headers(other)).status_code == 404
        mine = {record["id"] for record in server.get("/v1/campaign", headers=_headers(person)).json()["campaigns"]}
        theirs = {record["id"] for record in server.get("/v1/campaign", headers=_headers(other)).json()["campaigns"]}
        assert world["id"] in mine and world["id"] not in theirs


class TestFactions:
    def test_factions_nest_by_kind_and_never_in_a_cycle(self, server: TestClient, person: Any) -> None:
        house = _create(server, person, "faction", name="House Vell", kind="family", entry=ENTRY)
        assert house["description"] == "A port city."
        cadet = _create(server, person, "faction", name="The Cadet Line", kind="family", parent_id=house["id"])
        assert _put(server, person, "faction", house, parent_id=cadet["id"]).status_code == 422
        response = server.post("/v1/faction", json={"faction": {"name": "Odd", "kind": "empire"}}, headers=_headers(person))
        assert response.status_code == 422, response.text

    def test_a_faction_belongs_to_a_world(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        guild = _create(server, person, "faction", name="Tide Guild", kind="guild", campaign_id=world["id"])
        assert guild["campaign_id"] == world["id"]


class TestItems:
    def test_an_item_has_a_kind_and_sensible_amounts(self, server: TestClient, person: Any) -> None:
        sword = _create(server, person, "item", name="Salt-steel sabre", kind="weapon", weight=1.5, base_value=40)
        assert (sword["kind"], sword["weight"]) == ("weapon", 1.5)
        for bad in ({"kind": "spaceship"}, {"weight": -1}, {"stack_size": 0}):
            response = server.post("/v1/item", json={"item": {"name": "Odd", **bad}}, headers=_headers(person))
            assert response.status_code == 422, (bad, response.text)

    def test_an_item_belongs_to_a_world(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        coin = _create(server, person, "item", name="Gull mark", kind="currency", campaign_id=world["id"])
        assert coin["campaign_id"] == world["id"]
        # Rule systems are zephyrex-vtt's rpg_systems: the wiki serves no game_system resource.
        assert server.get("/v1/game_system", headers=_headers(person)).status_code == 404

    def test_an_item_in_the_world_has_a_place_an_owner_and_a_count(self, server: TestClient, person: Any) -> None:
        sword = _create(server, person, "item", name="Gull-hilt dagger", kind="weapon")
        inn = _create(server, person, "location", name="The Anchor", kind="building")
        mira = _create(server, person, "person", name="Mira Vell")
        held = _create(server, person, "item_instance", item_id=sword["id"], location_id=inn["id"], owner_person_id=mira["id"], quantity=2)
        assert (held["location_id"], held["owner_person_id"], held["quantity"]) == (inn["id"], mira["id"], 2)
        response = server.post("/v1/item_instance", json={"item_instance": {"item_id": sword["id"], "quantity": 0}}, headers=_headers(person))
        assert response.status_code == 422, response.text


class TestInventory:
    def test_a_factions_hoard_is_what_it_carries(self, server: TestClient, person: Any) -> None:
        # The difference from zephyrex-vtt's rpg_state: no owner_faction_id on the item; a faction
        # holds things through EntityInventory, like any other entity (W8).
        guild = _create(server, person, "faction", name="Brine Syndicate", kind="criminal")
        coin = _create(server, person, "item", name="Brine bar", kind="currency")
        stack = _create(server, person, "item_instance", item_id=coin["id"], quantity=50)
        hoard = _create(
            server, person, "entity_inventory", target_entity_type="faction", target_entity_id=guild["id"], item_instance_id=stack["id"], quantity=50
        )
        assert (hoard["target_entity_type"], hoard["target_entity_id"], hoard["quantity"]) == ("faction", guild["id"], 50)
        listed = server.get(f"/v1/entity_inventory?target_entity_id={guild['id']}", headers=_headers(person)).json()["entity_inventories"]
        assert [row["id"] for row in listed] == [hoard["id"]]

    def test_an_unknown_carrier_type_or_an_empty_count_is_refused(self, server: TestClient, person: Any) -> None:
        coin = _create(server, person, "item", name="Copper", kind="currency")
        stack = _create(server, person, "item_instance", item_id=coin["id"])
        for bad in ({"target_entity_type": "planet", "quantity": 1}, {"target_entity_type": "person", "quantity": 0}):
            body = {"target_entity_id": "x", "item_instance_id": stack["id"], **bad}
            response = server.post("/v1/entity_inventory", json={"entity_inventory": body}, headers=_headers(person))
            assert response.status_code == 422, (bad, response.text)


def _worn_by(server: TestClient, user: Any, instance: dict[str, Any]) -> Any:
    """Who wears or wields an item instance: the person its place belongs to, when that place is one
    of their equipment slots or body parts (OBJECT_PLAN §4: equipping is a move). Else nobody."""
    if instance["location_id"] is None:
        return None
    place = server.get(f"/v1/location/{instance['location_id']}", headers=_headers(user)).json()["location"]
    return place["associated_person_id"] if place["kind"] in ("equipment_slot", "body_part") else None


class TestWornOrPacked:
    def test_an_item_in_a_slot_bound_to_a_person_is_worn_and_in_a_pack_it_is_not(self, server: TestClient, person: Any) -> None:
        mira = _create(server, person, "person", name="Mira of the Gull", kind="npc")
        hand = _create(server, person, "location", name="Right hand", kind="equipment_slot", associated_person_id=mira["id"])
        pack = _create(server, person, "location", name="Mira's pack", kind="container", associated_person_id=mira["id"])
        sabre = _create(server, person, "item", name="Gull sabre", kind="weapon")
        wielded = _create(server, person, "item_instance", item_id=sabre["id"], location_id=hand["id"])
        packed = _create(server, person, "item_instance", item_id=sabre["id"], location_id=pack["id"])
        loose = _create(server, person, "item_instance", item_id=sabre["id"])
        _create(server, person, "entity_inventory", target_entity_type="person", target_entity_id=mira["id"], item_instance_id=loose["id"])
        assert _worn_by(server, person, wielded) == mira["id"]
        assert _worn_by(server, person, packed) is None
        assert _worn_by(server, person, loose) is None
        slots = server.get(f"/v1/location?associated_person_id={mira['id']}", headers=_headers(person)).json()["locations"]
        assert {row["id"] for row in slots} == {hand["id"], pack["id"]}


class TestWorldIsFixed:
    """A record's world is fixed once set (rpg-ai A15's sync); moving is copy and delete."""

    def test_a_record_joins_a_world_but_never_leaves_or_switches(self, server: TestClient, person: Any) -> None:
        first = _create(server, person, "campaign", name="First World")
        second = _create(server, person, "campaign", name="Second World")
        for resource, fields in (
            ("location", {"name": "Driftwood Pier", "kind": "building"}),
            ("faction", {"name": "Pier Watch", "kind": "military"}),
            ("item", {"name": "Pier lantern", "kind": "misc"}),
            ("person", {"name": "Old Tamsin", "kind": "npc"}),
            ("hook", {"name": "Who lit the pier?", "kind": "mystery"}),
        ):
            record = _create(server, person, resource, **fields)
            joined = _put(server, person, resource, record, campaign_id=first["id"])
            assert joined.status_code == 200, (resource, joined.text)
            assert _put(server, person, resource, record, campaign_id=second["id"]).status_code == 422, resource
            assert _put(server, person, resource, record, campaign_id=None).status_code == 422, resource
            assert _put(server, person, resource, record, campaign_id=first["id"]).status_code == 200, resource


class TestJournalsAndPosts:
    def test_a_journal_has_a_kind_an_author_a_place_and_a_world(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        bard = _create(server, person, "person", name="Wren the Bard", campaign_id=world["id"])
        inn = _create(server, person, "location", name="The Lantern", kind="building", campaign_id=world["id"])
        diary = _create(
            server, person, "journal", name="Wren's diary", kind="in_world_diary", author_person_id=bard["id"], location_id=inn["id"],
            campaign_id=world["id"], entry=ENTRY,
        )
        assert (diary["kind"], diary["author_person_id"], diary["location_id"], diary["campaign_id"]) == ("in_world_diary", bard["id"], inn["id"], world["id"])
        assert diary["description"] == "A port city."
        response = server.post("/v1/journal", json={"journal": {"name": "Odd", "kind": "poem"}}, headers=_headers(person))
        assert response.status_code == 422, response.text

    def test_posts_sit_on_any_record_pinned_first(self, server: TestClient, person: Any) -> None:
        keep = _create(server, person, "location", name="The Keep", kind="building")
        pinned = _create(server, person, "entity_post", target_entity_type="location", target_entity_id=keep["id"], name="Rumour", position="pinned_top")
        _create(server, person, "entity_post", target_entity_type="location", target_entity_id=keep["id"], name="History", ordinal=1)
        assert pinned["position"] == "pinned_top"
        posts = server.get(f"/v1/entity_post?target_entity_id={keep['id']}", headers=_headers(person)).json()["entity_posts"]
        assert {post["name"] for post in posts} == {"Rumour", "History"}
        for bad in ({"position": "sideways"}, {"target_entity_type": "planet"}, {"ordinal": -1}):
            body = {"target_entity_type": "location", "target_entity_id": keep["id"], "name": "Odd", **bad}
            response = server.post("/v1/entity_post", json={"entity_post": body}, headers=_headers(person))
            assert response.status_code == 422, (bad, response.text)


class TestSessionReports:
    """rpg-ai A24: a session report is a journal of kind session_report in its campaign."""

    def _cast(self, server: TestClient, person: Any, world: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        mira = _create(server, person, "person", name="Mira of the Lantern", campaign_id=world["id"])
        gull = _create(server, person, "location", name="Gull Rock", kind="region", campaign_id=world["id"])
        return mira, gull

    def test_written_and_read_back_with_its_mentions_and_title_kept_out_of_the_body(
        self, server: TestClient, person: Any, world: dict[str, Any]
    ) -> None:
        mira, gull = self._cast(server, person, world)
        report = {
            "campaign_id": world["id"],
            "title": "Session 4: the Gull Rock ambush",
            "body": "The party was ambushed.\n\nMira held the line.",
            "session_number": 4,
            "mentions": [
                {"target_entity_type": "person", "target_entity_id": mira["id"]},
                {"target_entity_type": "location", "target_entity_id": gull["id"]},
            ],
        }
        written = server.post("/v1/session_report", json={"session_report": report}, headers=_headers(person))
        # It creates a journal: 201 in both editions (custom_route's status_code, server-framework c95b34f4).
        assert written.status_code == 201, written.text
        saved = written.json()["session_report"]
        assert saved["title"] == "Session 4: the Gull Rock ambush"
        assert "Session 4" not in saved["text"]
        assert saved["text"] == "The party was ambushed.\nMira held the line.\nMentioned: Mira of the Lantern, Gull Rock"
        assert [(m["target_entity_type"], m["target_entity_id"]) for m in saved["mentions"]] == [("person", mira["id"]), ("location", gull["id"])]
        again = server.get(f"/v1/session_report/{saved['id']}", headers=_headers(person)).json()["session_report"]
        assert again == saved
        journal = server.get(f"/v1/journal/{saved['id']}", headers=_headers(person)).json()["journal"]
        assert (journal["kind"], journal["session_number"], journal["campaign_id"]) == ("session_report", 4, world["id"])

    def test_a_mention_outside_the_campaign_or_another_persons_campaign_is_refused(
        self, server: TestClient, person: Any, other: Any, world: dict[str, Any]
    ) -> None:
        stranger = _create(server, person, "person", name="A stranger")
        report = {
            "campaign_id": world["id"],
            "title": "Session 5",
            "body": "Quiet.",
            "mentions": [{"target_entity_type": "person", "target_entity_id": stranger["id"]}],
        }
        response = server.post("/v1/session_report", json={"session_report": report}, headers=_headers(person))
        assert response.status_code == 422, response.text
        theirs = server.post("/v1/session_report", json={"session_report": {**report, "mentions": []}}, headers=_headers(other))
        assert theirs.status_code == 404, theirs.text

    def test_the_abilities_write_and_read_the_same_record(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        write = loaded_ability(registry, "rpg_core", "session_report")
        read = loaded_ability(registry, "rpg_core", "session_report_get")
        assert write is not None and read is not None
        made = write(registry, str(person.id), campaign_id=world["id"], title="Session 6", body="Calm seas.")
        report = read(registry, str(person.id), made["id"])
        assert (report["title"], report["text"], report["mentions"]) == ("Session 6", "Calm seas.", [])


class TestWorldEntities:
    """rpg-ai A15: a campaign's changes since a time, tombstones included, paged."""

    def test_a_sync_sees_changes_tombstones_and_pages(self, server: TestClient, person: Any, other: Any) -> None:
        world_id = _create(server, person, "campaign", name="Sync World")["id"]
        harbour = _create(server, person, "location", name="Harbour", kind="district", campaign_id=world_id, entry=ENTRY)
        _create(server, person, "person", name="Dockmaster Ilse", campaign_id=world_id)
        _create(server, person, "faction", name="Harbour Guild", kind="guild", campaign_id=world_id)
        doomed = _create(server, person, "item", name="Cracked lantern", kind="misc", campaign_id=world_id)
        _create(server, person, "location", name="Elsewhere", kind="region")  # no world: never listed

        everything = server.get(f"/v1/world_entity?campaign_id={world_id}", headers=_headers(person))
        assert everything.status_code == 200, everything.text
        page = everything.json()
        by_name = {entity["name"]: entity for entity in page["world_entities"]}
        assert set(by_name) == {"Harbour", "Dockmaster Ilse", "Harbour Guild", "Cracked lantern"}
        assert by_name["Harbour"] | {"updated_at": None} == {
            "id": harbour["id"], "kind": "location", "name": "Harbour", "aliases": [], "summary": "A port city.",
            "picture": None, "updated_at": None, "deleted": False, "setting_id": None, "canon": False, "canon_level": None,
            "keywords": [], "voice": None, "tts_voice": None, "person_kind": None, "unnamed_as": None, "gender": None, "routine": None, "motivations": None, "invariants": None, "tags": [], "relationships": None, "lore": None, "provenance": "homebrew", "source": None, "gm_only": False, "location_id": None, "parent_id": None,
        }
        assert page["next"] is None

        current = server.get(f"/v1/item/{doomed['id']}", headers=_headers(person))
        gone = server.delete(f"/v1/item/{doomed['id']}", headers=_headers(person, **{"If-Match": current.headers["ETag"]}))
        assert gone.status_code in (200, 204), gone.text
        last_seen = max(entity["updated_at"] for entity in page["world_entities"])
        changed = server.get(f"/v1/world_entity?campaign_id={world_id}&since={last_seen}&kinds=item", headers=_headers(person)).json()
        assert [(entity["id"], entity["deleted"]) for entity in changed["world_entities"]][-1] == (doomed["id"], True)

        seen: list[str] = []
        after = ""
        while True:
            step = server.get(f"/v1/world_entity?campaign_id={world_id}&limit=1{after}", headers=_headers(person)).json()
            seen.extend(entity["id"] for entity in step["world_entities"])
            if step["next"] is None:
                break
            after = f"&after={step['next']}"
        assert len(seen) == len(set(seen)) == 4

        assert server.get(f"/v1/world_entity?campaign_id={world_id}", headers=_headers(other)).status_code == 404
        assert server.get(f"/v1/world_entity?campaign_id={world_id}&kinds=dragon", headers=_headers(person)).status_code == 422


class TestHooks:
    """The plot-hook DAG (OBJECT_PLAN §6, moved from vtt's rpg_state) and who is on each hook."""

    def test_a_hook_has_a_kind_givers_an_entry_and_a_world(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        captain = _create(server, person, "person", name="Captain Ross", campaign_id=world["id"])
        guild = _create(server, person, "faction", name="Salt Guild", kind="guild", campaign_id=world["id"])
        hook = _create(
            server, person, "hook", name="Recover the relic", kind="major_quest", giver_person_id=captain["id"],
            giver_faction_id=guild["id"], campaign_id=world["id"], entry=ENTRY,
        )
        assert (hook["kind"], hook["giver_person_id"], hook["giver_faction_id"], hook["campaign_id"]) == (
            "major_quest", captain["id"], guild["id"], world["id"],
        )
        assert hook["description"] == "A port city."
        response = server.post("/v1/hook", json={"hook": {"name": "Odd", "kind": "sidequest"}}, headers=_headers(person))
        assert response.status_code == 422, response.text

    def test_dependencies_form_a_dag_with_no_cycles_or_repeats(self, server: TestClient, person: Any) -> None:
        find, reach, slay = (_create(server, person, "hook", name=name, kind="objective") for name in ("Find", "Reach", "Slay"))
        _create(server, person, "hook_dependency", parent_hook_id=find["id"], child_hook_id=reach["id"], reason="The map")
        _create(server, person, "hook_dependency", parent_hook_id=reach["id"], child_hook_id=slay["id"])
        for parent, child in ((slay, find), (reach, find), (find, find), (find, reach)):
            body = {"parent_hook_id": parent["id"], "child_hook_id": child["id"]}
            response = server.post("/v1/hook_dependency", json={"hook_dependency": body}, headers=_headers(person))
            assert response.status_code == 422, (parent["name"], child["name"], response.text)
        waits = server.get(f"/v1/hook_dependency?child_hook_id={slay['id']}", headers=_headers(person)).json()["hook_dependencies"]
        assert [edge["parent_hook_id"] for edge in waits] == [reach["id"]]

    def test_people_and_organisations_take_a_hook_once_and_progress(self, server: TestClient, person: Any) -> None:
        hook = _create(server, person, "hook", name="Slay five wolves", kind="side_quest")
        hunter = _create(server, person, "person", name="Hunter Brin")
        lodge = _create(server, person, "faction", name="Hunters' Lodge", kind="guild")
        mine = _create(server, person, "person_hook", person_id=hunter["id"], hook_id=hook["id"], status="active", progress=3)
        assert (mine["status"], mine["progress"]) == ("active", 3)
        _create(server, person, "faction_hook", faction_id=lodge["id"], hook_id=hook["id"], status="available")
        again = server.post("/v1/person_hook", json={"person_hook": {"person_id": hunter["id"], "hook_id": hook["id"]}}, headers=_headers(person))
        assert again.status_code == 422, again.text
        done = _put(server, person, "person_hook", mine, status="completed", progress=5)
        assert done.status_code == 200, done.text
        for bad in ({"status": "x" * 41}, {"progress": -1}):
            assert _put(server, person, "person_hook", mine, **bad).status_code == 422, bad

    def test_deleting_a_hook_takes_its_dependencies_and_progress(self, server: TestClient, person: Any) -> None:
        before, doomed, after = (_create(server, person, "hook", name=name) for name in ("Before", "Doomed", "After"))
        _create(server, person, "hook_dependency", parent_hook_id=before["id"], child_hook_id=doomed["id"])
        _create(server, person, "hook_dependency", parent_hook_id=doomed["id"], child_hook_id=after["id"])
        scout = _create(server, person, "person", name="Scout Ilka")
        _create(server, person, "person_hook", person_id=scout["id"], hook_id=doomed["id"], status="active")
        current = server.get(f"/v1/hook/{doomed['id']}", headers=_headers(person))
        gone = server.delete(f"/v1/hook/{doomed['id']}", headers=_headers(person, **{"If-Match": current.headers["ETag"]}))
        assert gone.status_code in (200, 204), gone.text
        for query in (f"parent_hook_id={doomed['id']}", f"child_hook_id={doomed['id']}"):
            assert server.get(f"/v1/hook_dependency?{query}", headers=_headers(person)).json()["hook_dependencies"] == []
        assert server.get(f"/v1/person_hook?hook_id={doomed['id']}", headers=_headers(person)).json()["person_hooks"] == []

    def test_hooks_never_reach_the_lorebook_sync(self, server: TestClient, person: Any) -> None:
        secret_world = _create(server, person, "campaign", name="Secret World")
        _create(server, person, "hook", name="The baron is the cultist", kind="mystery", campaign_id=secret_world["id"])
        page = server.get(f"/v1/world_entity?campaign_id={secret_world['id']}", headers=_headers(person)).json()
        assert page["world_entities"] == []
        assert server.get(f"/v1/world_entity?campaign_id={secret_world['id']}&kinds=hook", headers=_headers(person)).status_code == 422


class TestTaxonomy:
    """W6: tags, categories, races and the rest in a tree, and statuses, on any record."""

    def test_taxa_form_a_tree_with_kinds_colours_and_a_world(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        nobility = _create(server, person, "taxon", name="Nobility", kind="tag", colour="#a83232", campaign_id=world["id"])
        house = _create(server, person, "taxon", name="House Vell", kind="tag", parent_id=nobility["id"], campaign_id=world["id"])
        assert (house["parent_id"], house["campaign_id"], nobility["colour"]) == (nobility["id"], world["id"], "#a83232")
        assert _put(server, person, "taxon", nobility, parent_id=house["id"]).status_code == 422
        for bad in ({"kind": "flavour"}, {"colour": "red"}):
            response = server.post("/v1/taxon", json={"taxon": {"name": "Odd", **bad}}, headers=_headers(person))
            assert response.status_code == 422, (bad, response.text)
        assert _put(server, person, "taxon", house, campaign_id=None).status_code == 422

    def test_a_record_takes_a_taxon_once_and_loses_it_when_the_taxon_goes(self, server: TestClient, person: Any) -> None:
        elf = _create(server, person, "taxon", name="Elf", kind="race")
        ilse = _create(server, person, "person", name="Ilse Moonbrook")
        _create(server, person, "entity_taxon", taxon_id=elf["id"], target_entity_type="person", target_entity_id=ilse["id"])
        body = {"taxon_id": elf["id"], "target_entity_type": "person", "target_entity_id": ilse["id"]}
        again = server.post("/v1/entity_taxon", json={"entity_taxon": body}, headers=_headers(person))
        assert again.status_code == 422, again.text
        odd = server.post("/v1/entity_taxon", json={"entity_taxon": {**body, "target_entity_type": "planet"}}, headers=_headers(person))
        assert odd.status_code == 422, odd.text
        current = server.get(f"/v1/taxon/{elf['id']}", headers=_headers(person))
        gone = server.delete(f"/v1/taxon/{elf['id']}", headers=_headers(person, **{"If-Match": current.headers["ETag"]}))
        assert gone.status_code in (200, 204), gone.text
        left = server.get(f"/v1/entity_taxon?target_entity_id={ilse['id']}", headers=_headers(person)).json()["entity_taxons"]
        assert left == []

    def test_a_record_has_one_status_at_a_time(self, server: TestClient, person: Any) -> None:
        alive = _create(server, person, "status", name="Alive", kind="entity_status", colour="#32a852")
        dead = _create(server, person, "status", name="Dead", kind="entity_status")
        bran = _create(server, person, "person", name="Bran the Old")
        held = _create(server, person, "entity_status", status_id=alive["id"], target_entity_type="person", target_entity_id=bran["id"])
        body = {"status_id": dead["id"], "target_entity_type": "person", "target_entity_id": bran["id"]}
        second = server.post("/v1/entity_status", json={"entity_status": body}, headers=_headers(person))
        assert second.status_code == 422, second.text
        changed = _put(server, person, "entity_status", held, status_id=dead["id"])
        assert changed.status_code == 200, changed.text
        assert changed.json()["entity_status"]["status_id"] == dead["id"]


class TestRelations:
    """W5: relations between people and organisations, with attitude, colour and a mirror."""

    def test_people_and_organisations_relate_with_one_end_a_side(self, server: TestClient, person: Any) -> None:
        guard = _create(server, person, "faction", name="City Guard", kind="military")
        thieves = _create(server, person, "faction", name="Thieves' Guild", kind="criminal")
        vex = _create(server, person, "person", name="Vex")
        rivalry = _create(
            server, person, "relationship", faction_id=guard["id"], target_faction_id=thieves["id"], kind="rival", intensity=-0.8, colour="#ff0000",
        )
        assert (rivalry["faction_id"], rivalry["target_faction_id"], rivalry["intensity"]) == (guard["id"], thieves["id"], -0.8)
        member = _create(server, person, "relationship", person_id=vex["id"], target_faction_id=thieves["id"], kind="member_of")
        assert member["target_faction_id"] == thieves["id"]
        for bad in (
            {"person_id": vex["id"], "faction_id": guard["id"], "target_faction_id": thieves["id"]},
            {"faction_id": guard["id"]},
            {"faction_id": guard["id"], "target_faction_id": guard["id"]},
            {"faction_id": guard["id"], "target_faction_id": thieves["id"], "colour": "crimson"},
        ):
            response = server.post("/v1/relationship", json={"relationship": {"kind": "rival", **bad}}, headers=_headers(person))
            assert response.status_code == 422, (bad, response.text)

    def test_a_mirror_reads_the_other_way_and_stays_in_step(self, server: TestClient, person: Any) -> None:
        mira = _create(server, person, "person", name="Mira")
        guild = _create(server, person, "faction", name="Lantern Guild", kind="guild")
        serves = _create(server, person, "relationship", person_id=mira["id"], target_faction_id=guild["id"], kind="serves", intensity=0.5)
        wrong = {"person_id": mira["id"], "target_faction_id": guild["id"], "kind": "serves", "mirror_relationship_id": serves["id"]}
        assert server.post("/v1/relationship", json={"relationship": wrong}, headers=_headers(person)).status_code == 422
        employs = _create(
            server, person, "relationship", faction_id=guild["id"], target_person_id=mira["id"], kind="serves", intensity=0.5,
            mirror_relationship_id=serves["id"],
        )
        assert server.get(f"/v1/relationship/{serves['id']}", headers=_headers(person)).json()["relationship"]["mirror_relationship_id"] == employs["id"]
        assert _put(server, person, "relationship", serves, intensity=-0.2, colour="#123456").status_code == 200
        mirrored = server.get(f"/v1/relationship/{employs['id']}", headers=_headers(person)).json()["relationship"]
        assert (mirrored["intensity"], mirrored["colour"]) == (-0.2, "#123456")
        current = server.get(f"/v1/relationship/{serves['id']}", headers=_headers(person))
        gone = server.delete(f"/v1/relationship/{serves['id']}", headers=_headers(person, **{"If-Match": current.headers["ETag"]}))
        assert gone.status_code in (200, 204), gone.text
        assert server.get(f"/v1/relationship/{employs['id']}", headers=_headers(person)).status_code == 404


class TestNarrativeState:
    """W56, W57, from dh-campaign's tracker: requirements, resolution, dispositions, influences."""

    def test_a_requirement_is_an_expression_and_its_hooks_become_the_edges(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        approach, null, vox = (_create(server, person, "hook", name=name, campaign_id=world["id"]) for name in ("Approach", "Discover the null", "Vox ghost"))
        requires = {"all": [approach["id"], {"any": [{"char": {"skill": ["psyniscience", "forbidden-lore"]}}, null["id"]]}]}
        assert _put(server, person, "hook", vox, requires=requires, excuse="Only a psyker or a scholar hears it").status_code == 200
        parents = server.get(f"/v1/hook_dependency?child_hook_id={vox['id']}", headers=_headers(person)).json()["hook_dependencies"]
        assert {edge["parent_hook_id"] for edge in parents} == {approach["id"], null["id"]}
        by_hand = {"parent_hook_id": null["id"], "child_hook_id": vox["id"]}
        assert server.post("/v1/hook_dependency", json={"hook_dependency": by_hand}, headers=_headers(person)).status_code == 422
        assert _put(server, person, "hook", vox, requires=approach["id"]).status_code == 200
        parents = server.get(f"/v1/hook_dependency?child_hook_id={vox['id']}", headers=_headers(person)).json()["hook_dependencies"]
        assert [edge["parent_hook_id"] for edge in parents] == [approach["id"]]
        for bad in ({"all": "x"}, {"char": {"skill": 3}}, "no-such-hook", {"any": [vox["id"]]}):
            assert _put(server, person, "hook", approach if bad != "no-such-hook" else vox, requires=bad).status_code == 422, bad

    def test_the_plot_state_follows_resolution_and_checks(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        world_id = _create(server, person, "campaign", name="Plot World")["id"]
        first = _create(server, person, "hook", name="Arrive", campaign_id=world_id)
        second = _create(server, person, "hook", name="Hear the story", campaign_id=world_id, requires=first["id"], excuse="Renn won't talk to strangers")
        heard = _create(server, person, "hook", name="Hear the ghost", campaign_id=world_id, requires={"all": [first["id"], {"char": {"skill": "psyniscience"}}]})
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        plot = loaded_ability(registry, "rpg_core", "plot_state")
        states = {hook["name"]: (hook["state"], hook["excuse"]) for hook in plot(registry, str(person.id), world_id)}
        assert states == {"Arrive": ("available", None), "Hear the story": ("blocked", "Renn won't talk to strangers"), "Hear the ghost": ("blocked", None)}
        report = _create(server, person, "journal", name="Session 1", kind="session_report", campaign_id=world_id)
        assert _put(server, person, "hook", first, resolved_at="2026-11-21T10:00:00", resolved_journal_id=report["id"]).status_code == 200
        states = {hook["name"]: hook["state"] for hook in plot(registry, str(person.id), world_id)}
        assert states == {"Arrive": "resolved", "Hear the story": "available", "Hear the ghost": "needs_check"}
        assert second["requires"] is not None and heard["requires"] is not None

    def test_dispositions_have_one_default_a_target_and_an_attitude_from_the_scale(self, server: TestClient, person: Any) -> None:
        brae = _create(server, person, "person", name="Brae Edric")
        story = _create(server, person, "hook", name="Hear the dock story")
        _create(server, person, "disposition", person_id=brae["id"], target_kind="party", attitude="cautious-neutral", is_default=True)
        _create(server, person, "disposition", person_id=brae["id"], target_kind="party", attitude="wary", trigger_hook_id=story["id"], note="She knows what they're circling")
        _create(server, person, "disposition", person_id=brae["id"], target_kind="party", attitude="guarded", trigger_hook_id=story["id"])
        for bad in (
            {"target_kind": "party", "attitude": "neutral", "is_default": True},
            {"target_kind": "party", "attitude": "smug", "is_default": True},
            {"target_kind": "person", "attitude": "neutral", "is_default": True},
            {"target_kind": "party", "attitude": "neutral"},
            {"target_kind": "crowd", "attitude": "neutral", "is_default": True},
        ):
            response = server.post("/v1/disposition", json={"disposition": {"person_id": brae["id"], **bad}}, headers=_headers(person))
            assert response.status_code == 422, (bad, response.text)
        rows = server.get(f"/v1/disposition?person_id={brae['id']}", headers=_headers(person)).json()["dispositions"]
        assert sorted(row["attitude"] for row in rows) == ["cautious-neutral", "guarded", "wary"]

    def test_a_hook_can_change_a_relation(self, server: TestClient, person: Any) -> None:
        osric = _create(server, person, "person", name="Pell Osric")
        corvyn = _create(server, person, "person", name="Corvyn Edric")
        tie = _create(server, person, "relationship", person_id=osric["id"], target_person_id=corvyn["id"], kind="subordinate", intensity=-1)
        found = _create(server, person, "hook", name="Find Osric")
        loosened = _create(server, person, "relation_influence", relationship_id=tie["id"], hook_id=found["id"], to_intensity=-0.4, note="The conditioning loosens")
        assert loosened["to_intensity"] == -0.4
        bad = {"relationship_id": tie["id"], "hook_id": found["id"], "to_intensity": 2}
        assert server.post("/v1/relation_influence", json={"relation_influence": bad}, headers=_headers(person)).status_code == 422


class TestSettings:
    """S6 (rpg-ai DESIGN "Settings and systems"): settings enclose campaigns; a setting's records with
    no campaign are its canon, read by rpg-ai's canon notices."""

    def test_a_setting_encloses_campaigns_and_its_campaign_less_records_are_canon(
        self, server: TestClient, person: Any, other: Any
    ) -> None:
        grim = _create(server, person, "setting", name="The Grim Future", entry=ENTRY)
        solenne = _create(server, person, "campaign", name="Solenne", setting_id=grim["id"])
        assert solenne["setting_id"] == grim["id"]
        canon = _create(server, person, "faction", name="Adeptus Mechanicus", kind="religious", setting_id=grim["id"], canon_level="common")
        assert (canon["setting_id"], canon["campaign_id"], canon["canon_level"]) == (grim["id"], None, "common")
        local = _create(server, person, "person", name="Magos Rech", campaign_id=solenne["id"], setting_id=grim["id"])
        assert local["setting_id"] == grim["id"]
        elsewhere = _create(server, person, "setting", name="Elsewhere")
        refused = [
            ("person", {"name": "Wrong world", "campaign_id": solenne["id"], "setting_id": elsewhere["id"]}),
            ("faction", {"name": "Odd level", "setting_id": grim["id"], "canon_level": "rumoured"}),
        ]
        for resource, body in refused:
            response = server.post(f"/v1/{resource}", json={resource: body}, headers=_headers(person))
            assert response.status_code == 422, (resource, response.text)
        theirs = server.post("/v1/faction", json={"faction": {"name": "Squatters", "setting_id": grim["id"]}}, headers=_headers(other))
        assert theirs.status_code == 422, theirs.text
        assert _put(server, person, "faction", canon, setting_id=elsewhere["id"]).status_code == 422
        assert _put(server, person, "campaign", solenne, setting_id=elsewhere["id"]).status_code == 422

    def test_a_setting_takes_a_unique_slug_fixed_once_set(self, server: TestClient, person: Any, other: Any) -> None:
        # The seeded Reality holds "reality", so a person's own takes the next number.
        own = _create(server, person, "setting", name="Reality")
        assert own["slug"] == "reality-2"
        realm = _create(server, person, "setting", name="Realm", slug="slug-realm")
        assert realm["slug"] == "slug-realm"
        clash = server.post("/v1/setting", json={"setting": {"name": "Theirs", "slug": "slug-realm"}}, headers=_headers(other))
        assert clash.status_code == 409, clash.text
        bad = server.post("/v1/setting", json={"setting": {"name": "Bad", "slug": "Bad Slug"}}, headers=_headers(person))
        assert bad.status_code == 422, bad.text
        assert _put(server, person, "setting", realm, slug="another").status_code == 422
        kept = _put(server, person, "setting", realm, slug="slug-realm", name="Realm Renamed")
        assert kept.status_code == 200, kept.text
        assert kept.json()["setting"]["slug"] == "slug-realm"

    def test_the_seeded_settings_are_everyones_and_only_the_systems_to_change(
        self, server: TestClient, person: Any, other: Any
    ) -> None:
        from zephyrex.extensions.wiki_shared.Contract import SEED_SETTINGS  # type: ignore[import-not-found]

        listed = server.get("/v1/setting", headers=_headers(other))
        assert listed.status_code == 200, listed.text
        seeded = {one["slug"]: one for one in listed.json()["settings"] if one["slug"] in {s["slug"] for s in SEED_SETTINGS}}
        assert {slug: one["name"] for slug, one in seeded.items()} == {s["slug"]: s["name"] for s in SEED_SETTINGS}
        # Operator, 2026-11-23: Reality alone is seeded (it replaces Modern; no IP in public code).
        assert set(seeded) == {"reality"}
        forty_k = seeded["reality"]
        campaign = _create(server, other, "campaign", name="Dunmarch", setting_id=forty_k["id"])
        assert campaign["setting_id"] == forty_k["id"]
        assert server.get(f"/v1/setting/{forty_k['id']}", headers=_headers(person)).status_code == 200
        # The framework doesn't say a record exists to someone who may not change it.
        assert _put(server, person, "setting", forty_k, name="Mine now").status_code == 404
        assert server.delete(f"/v1/setting/{forty_k['id']}", headers=_headers(person)).status_code == 404

    def test_rpg_ai_reads_a_settings_canon_alone_or_with_a_campaign(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        realm = _create(server, person, "setting", name="Realm of Canon")
        campaign = _create(server, person, "campaign", name="Dunmarch", setting_id=realm["id"])
        terra = _create(server, person, "location", name="Terra", kind="planet", setting_id=realm["id"], canon_level="common")
        hive = _create(server, person, "location", name="Hive Dunmarch", kind="city", campaign_id=campaign["id"], setting_id=realm["id"])
        alone = server.get(f"/v1/world_entity?setting_id={realm['id']}", headers=_headers(person)).json()["world_entities"]
        assert [(entity["id"], entity["canon"], entity["canon_level"]) for entity in alone] == [(terra["id"], True, "common")]
        own = server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=_headers(person)).json()["world_entities"]
        assert [entity["id"] for entity in own] == [hive["id"]]
        both = server.get(f"/v1/world_entity?campaign_id={campaign['id']}&include_setting=true", headers=_headers(person)).json()["world_entities"]
        assert {(entity["id"], entity["canon"]) for entity in both} == {(terra["id"], True), (hive["id"], False)}
        assert server.get("/v1/world_entity", headers=_headers(person)).status_code == 422
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        canon = loaded_ability(registry, "rpg_core", "setting_canon")(registry, str(person.id), realm["id"])
        assert [entity["name"] for entity in canon["world_entities"]] == ["Terra"]
        synced = loaded_ability(registry, "rpg_core", "world_entities")(registry, str(person.id), campaign["id"], include_setting=True)
        assert {entity["name"] for entity in synced["world_entities"]} == {"Terra", "Hive Dunmarch"}


PNG = b"\x89PNG\r\n\x1a\n" + b"a small map" * 4


class TestPictures:
    """S2c (rpg-ai A31): a record's picture is its newest primary_image attachment (the framework's
    attachments, on cloud storage), read wherever the record is."""

    @pytest.fixture(autouse=True)
    def store(self, memory_store: dict[str, bytes]) -> dict[str, bytes]:
        return memory_store

    @staticmethod
    def _upload(server: TestClient, user: Any, name: str) -> dict[str, Any]:
        made = server.post(
            "/v1/asset/upload", params={"name": name}, content=PNG, headers=_headers(user, **{"Content-Type": "image/png"})
        )
        assert made.status_code == 201, made.text
        asset: dict[str, Any] = made.json()["asset"]
        return asset

    @staticmethod
    def _attach(server: TestClient, user: Any, asset: dict[str, Any], kind: str, record: dict[str, Any]) -> Any:
        body = {"attachment": {"asset_id": asset["id"], "target_entity_type": kind, "target_entity_id": record["id"], "role": "primary_image"}}
        return server.post("/v1/attachment", json=body, headers=_headers(user))

    @staticmethod
    def _pictures(server: TestClient, user: Any, campaign: dict[str, Any]) -> dict[str, Any]:
        listed = server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=_headers(user))
        assert listed.status_code == 200, listed.text
        return {entity["name"]: entity["picture"] for entity in listed.json()["world_entities"]}

    def test_world_entities_carry_each_records_newest_picture(self, server: TestClient, person: Any, other: Any) -> None:
        from zephyrex.testing.factories import if_match_of

        campaign = _create(server, person, "campaign", name="Pictured")
        terra = _create(server, person, "location", name="Terra", kind="planet", campaign_id=campaign["id"])
        _create(server, person, "person", name="Magos Rech", campaign_id=campaign["id"])
        first, second = self._upload(server, person, "terra.png"), self._upload(server, person, "terra-night.png")
        for asset in (first, second):
            assert self._attach(server, person, asset, "location", terra).status_code == 201
        pictures = self._pictures(server, person, campaign)
        assert pictures == {"Terra": f"/v1/asset/{second['id']}/content", "Magos Rech": None}
        content = server.get(pictures["Terra"], headers=_headers(person))
        assert (content.status_code, content.content) == (200, PNG)
        # Someone who can't see Terra can't attach to it or read its picture.
        assert server.get(pictures["Terra"], headers=_headers(other)).status_code == 404
        assert self._attach(server, other, self._upload(server, other, "mine.png"), "location", terra).status_code == 404
        # A deleted picture gives way to the one before, then to none.
        assert server.delete(f"/v1/asset/{second['id']}", headers=_headers(person, **if_match_of(second))).status_code == 204
        assert self._pictures(server, person, campaign)["Terra"] == f"/v1/asset/{first['id']}/content"
        assert server.delete(f"/v1/asset/{first['id']}", headers=_headers(person, **if_match_of(first))).status_code == 204
        assert self._pictures(server, person, campaign)["Terra"] is None


class TestPropertiesKitsTemplates:
    """S4b: a record's properties are the framework's record_metadata; a kit adds the keys a record
    lacks; a template is copied into campaigns with its properties and tags and is never a world fact."""

    @staticmethod
    def _properties(server: TestClient, user: Any, kind: str, record: dict[str, Any]) -> Any:
        return server.get("/v1/record_metadata/of", params={"target_entity_type": kind, "target_entity_id": record["id"]}, headers=_headers(user))

    @staticmethod
    def _property(server: TestClient, user: Any, kind: str, record: dict[str, Any], **fields: Any) -> Any:
        body = {"record_metadata": {"target_entity_type": kind, "target_entity_id": record["id"], **fields}}
        return server.post("/v1/record_metadata", json=body, headers=_headers(user))

    @staticmethod
    def _apply(server: TestClient, user: Any, kit: dict[str, Any], kind: str, record: dict[str, Any]) -> Any:
        body = {"application": {"target_entity_type": kind, "target_entity_id": record["id"]}}
        return server.post(f"/v1/property_kit/{kit['id']}/apply", json=body, headers=_headers(user))

    def test_a_kit_adds_the_keys_a_record_lacks(self, server: TestClient, person: Any, other: Any) -> None:
        campaign = _create(server, person, "campaign", name="Kitted")
        hive = _create(server, person, "location", name="Hive Sibellus", kind="city", campaign_id=campaign["id"])
        assert self._property(server, person, "location", hive, key="Population", value="9 billion", value_type="text").status_code == 201
        kit = _create(
            server,
            person,
            "property_kit",
            name="City",
            campaign_id=campaign["id"],
            properties=[{"key": "Population"}, {"key": "Tithe grade", "default": "Exactus"}, {"key": "Garrison", "value_type": "number", "default": 3, "is_private": True}],
        )
        first = self._apply(server, person, kit, "location", hive)
        assert first.status_code == 200, first.text
        assert first.json() == {"added": ["Tithe grade", "Garrison"], "skipped": ["Population"]}
        rows = {row["key"]: row for row in self._properties(server, person, "location", hive).json()["metadata"]}
        assert (rows["Population"]["value"], rows["Tithe grade"]["value"], rows["Garrison"]["value"]) == ("9 billion", "Exactus", "3")
        assert (rows["Garrison"]["value_type"], rows["Garrison"]["is_private"]) == ("number", True)
        assert self._apply(server, person, kit, "location", hive).json() == {"added": [], "skipped": ["Population", "Tithe grade", "Garrison"]}
        # Someone who can't see the kit, or the record, gets the same 404.
        theirs = _create(server, other, "location", name="Their Hive", kind="city")
        assert self._apply(server, other, kit, "location", theirs).status_code == 404
        assert self._properties(server, other, "location", hive).status_code == 404
        refused = server.post("/v1/property_kit", json={"property_kit": {"name": "Bad", "properties": [{"key": "A"}, {"key": "A"}]}}, headers=_headers(person))
        assert refused.status_code == 422, refused.text

    def test_a_template_is_copied_with_its_properties_and_tags_and_never_synced(self, server: TestClient, person: Any) -> None:
        campaign = _create(server, person, "campaign", name="Templated")
        template = _create(server, person, "person", name="Arbites Enforcer", kind="npc", is_template=True, entry=ENTRY)
        assert self._property(server, person, "person", template, key="Wounds", value="12", value_type="number").status_code == 201
        tag = _create(server, person, "taxon", name="Adeptus Arbites", kind="tag")
        shotgun = _create(server, person, "item", name="Combat shotgun", kind="weapon", is_template=True)
        gear = _create(server, person, "item_instance", item_id=shotgun["id"], owner_person_id=template["id"], durability=0.9)
        _create(server, person, "entity_inventory", item_instance_id=gear["id"], target_entity_type="person", target_entity_id=template["id"])
        _create(server, person, "entity_taxon", taxon_id=tag["id"], target_entity_type="person", target_entity_id=template["id"])
        made = server.post(
            "/v1/template/instantiate",
            json={"template": {"kind": "person", "template_id": template["id"], "campaign_id": campaign["id"], "name": "Proctor Vance"}},
            headers=_headers(person),
        )
        assert made.status_code == 201, made.text
        assert {key: made.json()[key] for key in ("kind", "name", "properties", "taxons", "items")} == {
            "kind": "person",
            "name": "Proctor Vance",
            "properties": 1,
            "taxons": 1,
            "items": 1,
        }
        # The copy carries its own shotgun, of the template's kind of shotgun, and owns it.
        held = server.get("/v1/entity_inventory", params={"target_entity_type": "person", "target_entity_id": made.json()["id"]}, headers=_headers(person))
        [holding] = held.json()["entity_inventories"]
        assert (holding["quantity"], holding["item_instance_id"] != gear["id"]) == (1, True)
        mine = server.get(f"/v1/item_instance/{holding['item_instance_id']}", headers=_headers(person)).json()["item_instance"]
        assert (mine["item_id"], mine["owner_person_id"], mine["durability"]) == (shotgun["id"], made.json()["id"], 0.9)
        copy = server.get(f"/v1/person/{made.json()['id']}", headers=_headers(person)).json()["person"]
        assert (copy["campaign_id"], copy["kind"], copy["is_template"], copy["description"]) == (campaign["id"], "npc", None, template["description"])
        assert [row["key"] for row in self._properties(server, person, "person", copy).json()["metadata"]] == ["Wounds"]
        # A campaign's own template stays out of its world sync too.
        _create(server, person, "location", name="Shrine (template)", kind="building", campaign_id=campaign["id"], is_template=True)
        synced = server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=_headers(person)).json()["world_entities"]
        assert [entity["name"] for entity in synced] == ["Proctor Vance"]
        # A record isn't a template, and never becomes one in place: Save as template copies it.
        plain = server.post("/v1/template/instantiate", json={"template": {"kind": "person", "template_id": copy["id"]}}, headers=_headers(person))
        assert plain.status_code == 422, plain.text
        assert _put(server, person, "person", copy, is_template=True).status_code == 422
        saved = server.post(
            "/v1/template/instantiate", json={"template": {"kind": "person", "template_id": copy["id"], "as_template": True}}, headers=_headers(person)
        )
        assert saved.status_code == 201, saved.text
        assert server.get(f"/v1/person/{saved.json()['id']}", headers=_headers(person)).json()["person"]["is_template"] is True


class TestNamesAndVoice:
    """S4c: aliases and keywords on every world record, and a person's AI voice, kept as JSON text
    and carried by world_entities for rpg-ai's lorebook (activation keys on name, aliases and keywords)."""

    def test_world_entities_carry_aliases_keywords_and_a_persons_voice(self, server: TestClient, person: Any) -> None:
        campaign = _create(server, person, "campaign", name="Named")
        marsh = _create(server, person, "location", name="Brindlemarsh", kind="city", campaign_id=campaign["id"], aliases=[" The Marsh Town ", "the marsh town"], keywords=["stilts"])
        assert (json.loads(marsh["aliases"]), json.loads(marsh["keywords"])) == (["The Marsh Town"], ["stilts"])
        voice = {"personality": "Gruff", "speech": "Short words.", "first_message": "What?", "examples": ["Holst: No."]}
        _create(server, person, "person", name="Holst", kind="npc", campaign_id=campaign["id"], aliases=["Old Holst"], voice=voice)
        listed = server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=_headers(person)).json()["world_entities"]
        by_name = {entity["name"]: entity for entity in listed}
        assert (by_name["Brindlemarsh"]["aliases"], by_name["Brindlemarsh"]["keywords"], by_name["Brindlemarsh"]["voice"]) == (["The Marsh Town"], ["stilts"], None)
        # Parity: the parts not given come back at their defaults.
        filled = {**voice, "system_prompt": "", "post_history_instructions": "", "depth_prompt": None, "talkativeness": 0.5, "across_chats": False}
        assert (by_name["Holst"]["aliases"], by_name["Holst"]["voice"]) == (["Old Holst"], filled)
        refused = [
            ("location", {"name": "Bad", "aliases": "not a list"}),
            ("person", {"name": "Bad", "voice": {"mood": "sad"}}),
            ("person", {"name": "Bad", "voice": {"talkativeness": 2}}),
            ("person", {"name": "Bad", "aliases": [f"n{index}" for index in range(51)]}),
        ]
        for resource, body in refused:
            response = server.post(f"/v1/{resource}", json={resource: body}, headers=_headers(person))
            assert response.status_code == 422, (resource, response.text)


class TestLore:
    """S4d: a record's lorebook activation (SillyTavern World Info's fields) in world_entities, so
    rpg-ai's activation reads it in the one sync."""

    def test_a_records_lore_block_is_filled_checked_and_synced(self, server: TestClient, person: Any) -> None:
        campaign = _create(server, person, "campaign", name="Lorebook")
        omen = _create(
            server, person, "journal", name="The Flicker", kind="lore", campaign_id=campaign["id"], keywords=["flicker"],
            lore={"position": "at_depth", "depth": 2, "selective_logic": "not_any", "secondary_keys": ["gate"]},
        )
        assert json.loads(omen["lore"])["probability"] == 100
        [synced] = server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=_headers(person)).json()["world_entities"]
        assert (synced["keywords"], synced["lore"]["position"], synced["lore"]["secondary_keys"], synced["lore"]["order"]) == (["flicker"], "at_depth", ["gate"], 100)
        for bad in ({"position": "middle"}, {"probability": 101}, {"colour": "red"}):
            response = server.post("/v1/journal", json={"journal": {"name": "Bad", "lore": bad}}, headers=_headers(person))
            assert response.status_code == 422, (bad, response.text)


class TestWorldEntitiesById:
    """rpg-ai's sandbox cast: persons from several campaigns, or a setting's canon, read by id,
    shaped as the sync shapes them; what the caller can't see is simply absent."""

    def test_named_records_wherever_they_are(self, server: TestClient, person: Any, other: Any) -> None:
        setting = _create(server, person, "setting", name="Cast Setting")
        first = _create(server, person, "campaign", name="Cast One", setting_id=setting["id"])
        second = _create(server, person, "campaign", name="Cast Two")
        mira = _create(server, person, "person", name="Mira", kind="npc", campaign_id=first["id"], voice={"personality": "Watchful."})
        ross = _create(server, person, "person", name="Ross", kind="npc", campaign_id=second["id"])
        saint = _create(server, person, "person", name="The Saint", kind="npc", setting_id=setting["id"])
        port = _create(server, person, "location", name="Port", kind="city", campaign_id=first["id"])
        mould = _create(server, person, "person", name="Mould", kind="npc", campaign_id=first["id"], is_template=True)
        theirs = _create(server, other, "person", name="Not yours", kind="npc")
        ids = [ross["id"], mira["id"], theirs["id"], saint["id"], mould["id"], "no-such-id", port["id"], mira["id"]]
        response = server.get(f"/v1/world_entity?ids={','.join(ids)}", headers=_headers(person))
        assert response.status_code == 200, response.text
        body = response.json()
        # In the order asked, each once; the other user's, the template and the unknown id absent.
        assert [(entity["name"], entity["kind"]) for entity in body["world_entities"]] == [
            ("Ross", "person"), ("Mira", "person"), ("The Saint", "person"), ("Port", "location"),
        ]
        by_name = {entity["name"]: entity for entity in body["world_entities"]}
        assert by_name["Mira"]["voice"]["personality"] == "Watchful."
        assert (by_name["The Saint"]["canon"], by_name["Mira"]["canon"], body["next"]) == (True, False, None)

    def test_refuses_no_ids_too_many_or_two_scopes(self, server: TestClient, person: Any, world: dict[str, Any]) -> None:
        for query in ("ids=", "ids=,,", "ids=" + ",".join(f"id{n}" for n in range(101)), f"ids=a&campaign_id={world['id']}"):
            assert server.get(f"/v1/world_entity?{query}", headers=_headers(person)).status_code == 422, query


def test_a_campaigns_framing_note_is_its_own_journal_kind(server: TestClient, person: Any) -> None:
    """rpg-ai opens a campaign from its framing note (Premise, Tone, Truths, Opening Situation)."""
    campaign = _create(server, person, "campaign", name="Framed")
    framing = _create(server, person, "journal", name="Framing", kind="campaign_framing", campaign_id=campaign["id"])
    assert framing["kind"] == "campaign_framing"


class TestProvenance:
    """A campaign says where it came from: homebrew, official or adapted, with its source."""

    def test_homebrew_unless_said_and_checked_together(self, server: TestClient, person: Any) -> None:
        plain = _create(server, person, "campaign", name="Mine")
        assert (plain["provenance"], plain["source"]) == ("homebrew", None)
        official = _create(server, person, "campaign", name="Purge", provenance="official", source=" Purge the Unclean, FFG, p. 4 ")
        assert (official["provenance"], official["source"]) == ("official", "Purge the Unclean, FFG, p. 4")
        for body in ({"name": "Bad", "provenance": "stolen"}, {"name": "Bad", "source": "A book"}):
            assert server.post("/v1/campaign", json={"campaign": body}, headers=_headers(person)).status_code == 422, body

        # A name change leaves them; a source alone can't go on a homebrew campaign; making one homebrew clears its source.
        renamed = _put(server, person, "campaign", official, name="Purge (cut)").json()["campaign"]
        assert (renamed["provenance"], renamed["source"]) == ("official", "Purge the Unclean, FFG, p. 4")
        current = server.get(f"/v1/campaign/{plain['id']}", headers=_headers(person))
        refused = server.put(
            f"/v1/campaign/{plain['id']}", json={"campaign": {"source": "A book"}}, headers=_headers(person, **{"If-Match": current.headers["ETag"]})
        )
        assert refused.status_code == 422, refused.text
        home = _put(server, person, "campaign", renamed, provenance="homebrew").json()["campaign"]
        assert (home["provenance"], home["source"]) == ("homebrew", None)
        adapted = _put(server, person, "campaign", home, provenance="adapted", source="Dark Heresy core, p. 300").json()["campaign"]
        cleared = _put(server, person, "campaign", adapted, source="").json()["campaign"]
        assert (cleared["provenance"], cleared["source"]) == ("adapted", None)

    def test_records_say_where_they_came_from_and_the_sync_carries_it(self, server: TestClient, person: Any) -> None:
        campaign = _create(server, person, "campaign", name="Sourced")
        relic = _create(server, person, "item", name="Relic", kind="misc", campaign_id=campaign["id"], provenance="official", source="Inquisitor's Handbook, p. 140")
        plain = _create(server, person, "location", name="Cellar", kind="room", campaign_id=campaign["id"])
        assert (relic["provenance"], plain["provenance"], plain["source"]) == ("official", "homebrew", None)
        assert server.post("/v1/person", json={"person": {"name": "Bad", "source": "A book"}}, headers=_headers(person)).status_code == 422
        synced = {entity["name"]: entity for entity in server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=_headers(person)).json()["world_entities"]}
        assert (synced["Relic"]["provenance"], synced["Relic"]["source"], synced["Cellar"]["provenance"]) == ("official", "Inquisitor's Handbook, p. 140", "homebrew")
        home = _put(server, person, "item", relic, provenance="homebrew").json()["item"]
        assert (home["provenance"], home["source"]) == ("homebrew", None)


class TestGmOnly:
    """Parity: a record kept to the GM (its private "GM only" property is true) says so in the sync,
    so rpg-ai keeps it out of players' prompts."""

    def test_the_gm_only_property_marks_a_record(self, server: TestClient, person: Any) -> None:
        campaign = _create(server, person, "campaign", name="Secrets")
        truth = _create(server, person, "journal", name="The Truth of the Flicker", kind="lore", campaign_id=campaign["id"])
        public = _create(server, person, "journal", name="Player briefing", kind="handout", campaign_id=campaign["id"])
        added = server.post(
            "/v1/record_metadata",
            json={"record_metadata": {"target_entity_type": "journal", "target_entity_id": truth["id"], "key": "GM only", "value": "true", "value_type": "boolean", "is_private": True}},
            headers=_headers(person),
        )
        assert added.status_code == 201, added.text
        synced = {entity["name"]: entity["gm_only"] for entity in server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=_headers(person)).json()["world_entities"]}
        assert synced == {"The Truth of the Flicker": True, "Player briefing": False}
        by_id = server.get(f"/v1/world_entity?ids={truth['id']},{public['id']}", headers=_headers(person)).json()["world_entities"]
        assert [entity["gm_only"] for entity in by_id] == [True, False]


class TestPlayStyles:
    """A scenario's play-style tags: the shared ones everyone uses, and anyone's own."""

    def test_campaigns_take_the_shared_play_styles_and_ones_own(self, server: TestClient, person: Any, other: Any) -> None:
        shared = server.get("/v1/taxon?kind=play_style", headers=_headers(other)).json()["taxons"]
        assert {"freeform", "combat-heavy", "mystery", "dungeon-crawl"} <= {row["name"] for row in shared}
        mystery = next(row for row in shared if row["name"] == "mystery")
        campaign = _create(server, person, "campaign", name="The Flicker")
        _create(server, person, "entity_taxon", taxon_id=mystery["id"], target_entity_type="campaign", target_entity_id=campaign["id"])
        mine = _create(server, person, "taxon", name="slow-burn", kind="play_style")
        _create(server, person, "entity_taxon", taxon_id=mine["id"], target_entity_type="campaign", target_entity_id=campaign["id"])
        tagged = server.get(f"/v1/entity_taxon?target_entity_type=campaign&target_entity_id={campaign['id']}", headers=_headers(person)).json()["entity_taxons"]
        assert {row["taxon_id"] for row in tagged} == {mystery["id"], mine["id"]}
        # The shared ones are everyone's to use and no one's to change.
        current = server.get(f"/v1/taxon/{mystery['id']}", headers=_headers(person))
        changed = server.put(f"/v1/taxon/{mystery['id']}", json={"taxon": {"name": "whodunit"}}, headers=_headers(person, **{"If-Match": current.headers["ETag"]}))
        assert changed.status_code == 404, changed.text


class TestPictureLinks:
    """A record's picture by https link (fandom, wikis…), before an uploaded one, cleared with ""."""

    def test_a_linked_picture_is_the_records_and_can_be_cleared(self, server: TestClient, person: Any) -> None:
        campaign = _create(server, person, "campaign", name="Linked")
        link = "https://static.wikia.nocookie.net/warhammer40k/images/a/a1/Inquisitor.jpg"
        ilsa = _create(server, person, "person", name="Ilsa", kind="npc", campaign_id=campaign["id"], picture_url=f" {link} ")
        assert ilsa["picture_url"] == link
        synced = server.get(f"/v1/world_entity?ids={ilsa['id']}", headers=_headers(person)).json()["world_entities"]
        assert synced[0]["picture"] == link
        for bad in ("http://example.com/a.png", "javascript:alert(1)"):
            refused = server.post("/v1/person", json={"person": {"name": "Bad", "picture_url": bad}}, headers=_headers(person))
            assert refused.status_code == 422, (bad, refused.text)
        cleared = _put(server, person, "person", ilsa, picture_url="").json()["person"]
        assert not cleared["picture_url"]
        assert server.get(f"/v1/world_entity?ids={ilsa['id']}", headers=_headers(person)).json()["world_entities"][0]["picture"] is None



_STEPS_SEEN: list[tuple[float, str]] = []


def _start(server: TestClient, user: Any, scenario_id: str, name: Optional[str] = None) -> dict[str, Any]:
    """POST …/instantiate (202, a start), then its GET until it ends; the finished start. Each step
    seen, with when, goes on _STEPS_SEEN (what a slow start spent its time on)."""
    import time

    accepted = server.post(f"/v1/campaign/{scenario_id}/instantiate", json={"instantiate": {"name": name} if name else {}}, headers=_headers(user))
    assert accepted.status_code == 202, accepted.text
    start = accepted.json()["start"]
    # Running in the background, or (START_IN_BACKGROUND off) already ended.
    assert start["scenario_id"] == scenario_id and start["state"] in ("running", "done", "failed"), start
    began = time.monotonic()
    deadline = began + 60
    _STEPS_SEEN.clear()
    while start["state"] == "running":
        if not _STEPS_SEEN or _STEPS_SEEN[-1][1] != start["step"]:
            _STEPS_SEEN.append((round(time.monotonic() - began, 1), str(start["step"])))
        assert time.monotonic() < deadline, start
        time.sleep(0.5)  # as the client polls (POLL_MS)
        polled = server.get(f"/v1/campaign_start/{start['id']}", headers=_headers(user))
        assert polled.status_code == 200, polled.text
        start = polled.json()["campaign_start"]
    return start


def _delete(server: TestClient, user: Any, resource: str, record_id: str) -> Any:
    """DELETE a record as a client does: with its version (ETag) as If-Match."""
    etag = server.get(f"/v1/{resource}/{record_id}", headers=_headers(user)).headers.get("etag", "")
    return server.delete(f"/v1/{resource}/{record_id}", headers={**_headers(user), "If-Match": etag})


def _start_with(server: TestClient, user: Any, scenario_id: str, pregens: list[str]) -> dict[str, Any]:
    """A start with the party's pregens, followed to its end."""
    import time

    accepted = server.post(f"/v1/campaign/{scenario_id}/instantiate", json={"instantiate": {"pregens": pregens}}, headers=_headers(user))
    assert accepted.status_code == 202, accepted.text
    start = accepted.json()["start"]
    deadline = time.monotonic() + 60
    while start["state"] == "running":
        assert time.monotonic() < deadline, start
        time.sleep(0.5)
        start = server.get(f"/v1/campaign_start/{start['id']}", headers=_headers(user)).json()["campaign_start"]
    return start


def _started(server: TestClient, user: Any, start: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """A done start's playthrough and id map."""
    assert start["state"] == "done", start
    campaign = server.get(f"/v1/campaign/{start['campaign_id']}", headers=_headers(user)).json()["campaign"]
    return campaign, json.loads(start["id_map"])

def _rows(body: dict[str, Any]) -> list[dict[str, Any]]:
    """A list answer's rows (its one list, whatever the resource's plural)."""
    return next(value for value in body.values() if isinstance(value, list))


class TestCopyOnStart:
    """Starting a scenario copies it into a playthrough: its own copy of every record and relation,
    references turned to the copies; the setting's canon stays shared; the scenario is untouched."""

    def test_a_playthrough_is_a_full_copy_with_its_references_remapped(self, server: TestClient, person: Any, other: Any) -> None:
        setting = _create(server, person, "setting", name="Copy Setting")
        canon = _create(server, person, "person", name="The Saint", kind="npc", setting_id=setting["id"])
        scenario = _create(server, person, "campaign", name="The Flicker", setting_id=setting["id"], is_scenario=True, provenance="official", source="Book, p. 1")
        tower = _create(server, person, "location", name="Tower", kind="building", campaign_id=scenario["id"])
        room = _create(server, person, "location", name="Lamp room", kind="room", campaign_id=scenario["id"], parent_id=tower["id"])
        mira = _create(
            server, person, "person", name="Mira", kind="npc", campaign_id=scenario["id"], location_id=room["id"],
            entry=[{"type": "p", "children": [{"text": "Keeps "}, {"type": "mention", "target_entity_type": "location", "target_entity_id": tower["id"], "children": [{"text": "the tower"}]}, {"text": "."}]}],
        )
        find = _create(server, person, "hook", name="Find the map", kind="objective", campaign_id=scenario["id"])
        relic = _create(server, person, "hook", name="Recover the relic", kind="major_quest", campaign_id=scenario["id"], requires=find["id"], giver_person_id=mira["id"])
        # Its requirement owns the dependency edge find → relic (copied, then kept by the copy's requirement).
        _create(server, person, "relationship", person_id=mira["id"], target_person_id=canon["id"], kind="serves", intensity=0.5)
        tag = _create(server, person, "taxon", name="Keepers", kind="tag", campaign_id=scenario["id"])
        _create(server, person, "entity_taxon", taxon_id=tag["id"], target_entity_type="person", target_entity_id=mira["id"])
        _create(server, person, "person", name="Mould", kind="npc", campaign_id=scenario["id"], is_template=True)

        run, ids = _started(server, person, _start(server, person, scenario["id"], "The Flicker, run 1"))
        assert (run["name"], run["scenario_id"], run["is_scenario"], run["provenance"], run["setting_id"]) == ("The Flicker, run 1", scenario["id"], False, "official", setting["id"])
        assert ids[scenario["id"]] == run["id"] and canon["id"] not in ids
        copies = {
            row["name"]: row
            for kind in ("person", "location", "hook")
            for row in _rows(server.get(f"/v1/{kind}?campaign_id={run['id']}", headers=_headers(person)).json())
        }
        # Every record copied (the template stayed), each reference turned to its copy.
        assert set(copies) == {"Mira", "Tower", "Lamp room", "Find the map", "Recover the relic"}
        assert copies["Lamp room"]["parent_id"] == ids[tower["id"]] and copies["Mira"]["location_id"] == ids[room["id"]]
        assert ids[tower["id"]] in copies["Mira"]["entry"] and tower["id"] not in copies["Mira"]["entry"]
        relic_copy = copies["Recover the relic"]
        assert ids[find["id"]] in relic_copy["requires"] and find["id"] not in relic_copy["requires"]
        assert relic_copy["giver_person_id"] == ids[mira["id"]]
        edges = server.get(f"/v1/hook_dependency?parent_hook_id={ids[find['id']]}", headers=_headers(person)).json()["hook_dependencies"]
        assert [edge["child_hook_id"] for edge in edges] == [ids[relic["id"]]]
        # A tie to the setting's canon is copied pointing at the same, shared canon.
        ties = server.get(f"/v1/relationship?person_id={ids[mira['id']]}", headers=_headers(person)).json()["relationships"]
        assert [tie["target_person_id"] for tie in ties] == [canon["id"]]
        # Its tag is the copy's own; the scenario keeps its own records.
        copied_tag = server.get(f"/v1/entity_taxon?target_entity_type=person&target_entity_id={ids[mira['id']]}", headers=_headers(person)).json()["entity_taxons"]
        assert [row["taxon_id"] for row in copied_tag] == [ids[tag["id"]]]
        held = _rows(server.get(f"/v1/person?campaign_id={scenario['id']}", headers=_headers(person)).json())
        assert sorted(row["name"] for row in held) == ["Mira", "Mould"]
        # Lists: scenarios alone, and a scenario's playthroughs.
        scenarios = server.get("/v1/campaign?is_scenario=true", headers=_headers(person)).json()["campaigns"]
        assert scenario["id"] in {row["id"] for row in scenarios} and run["id"] not in {row["id"] for row in scenarios}
        runs = server.get(f"/v1/campaign?scenario_id={scenario['id']}", headers=_headers(person)).json()["campaigns"]
        assert [row["id"] for row in runs] == [run["id"]]
        # Someone who can't see the scenario can't start it.
        assert server.post(f"/v1/campaign/{scenario['id']}/instantiate", json={"instantiate": {}}, headers=_headers(other)).status_code == 404


class TestStartingWithPictures:
    """Prod, 2026-11-21: a scenario whose records have pictures failed every start (attachments refuse
    plural creates then), leaving a half-copied campaign. Pictures are copied in one plural create, and a
    start that fails partway is undone."""

    @pytest.mark.usefixtures("memory_store")
    def test_a_scenario_with_pictures_starts_and_a_failed_start_leaves_nothing(self, server: TestClient, person: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        scenario = _create(server, person, "campaign", name="Voidship", is_scenario=True)
        captain = _create(server, person, "person", name="Captain Vell", kind="npc", campaign_id=scenario["id"])
        bridge = _create(server, person, "location", name="Bridge", kind="room", campaign_id=scenario["id"])
        for kind, record in (("person", captain), ("location", bridge)):
            asset = server.post("/v1/asset/upload", params={"name": f"{record['name']}.png"}, content=b"\x89PNG picture", headers={**_headers(person), "Content-Type": "image/png"})
            assert asset.status_code in (200, 201), asset.text
            attached = server.post(
                "/v1/attachment",
                json={"attachment": {"asset_id": asset.json()["asset"]["id"], "target_entity_type": kind, "target_entity_id": record["id"], "role": "primary_image"}},
                headers=_headers(person),
            )
            assert attached.status_code in (200, 201), attached.text

        rank = server.post(
            "/v1/record_metadata",
            json={"record_metadata": {"target_entity_type": "person", "target_entity_id": captain["id"], "key": "Rank", "value": "Captain", "value_type": "text", "is_private": True}},
            headers=_headers(person),
        )
        assert rank.status_code == 201, rank.text
        first_start = _start(server, person, scenario["id"], "Run 1")
        first, ids = _started(server, person, first_start)
        pictures = server.get(
            "/v1/attachment/of", params={"target_entity_type": "person", "target_entity_id": ids[captain["id"]], "role": "primary_image"}, headers=_headers(person)
        ).json()["attachments"]
        assert len(pictures) == 1

        properties = server.get(
            "/v1/record_metadata/of", params={"target_entity_type": "person", "target_entity_id": ids[captain["id"]]}, headers=_headers(person)
        ).json()["metadata"]
        assert [(row["key"], row["value"], row["is_private"]) for row in properties] == [("Rank", "Captain", True)]

        # A start is its starter's alone.
        other = create_user(server)
        assert server.get(f"/v1/campaign_start/{first_start['id']}", headers=_headers(other)).status_code == 404

        # A start failing after the copies are made takes them all back.
        from zephyrex.extensions.rpg_core import Scenarios  # type: ignore[import-not-found]

        def broken(copying: Any) -> None:
            raise RuntimeError("the second pass failed")

        monkeypatch.setattr(Scenarios, "finish", broken)
        before = {row["id"] for row in server.get("/v1/campaign", headers=_headers(person)).json()["campaigns"]}
        failed = _start(server, person, scenario["id"], "Run 2")
        assert (failed["state"], failed["error"]) == ("failed", "the second pass failed")
        after = {row["id"] for row in server.get("/v1/campaign", headers=_headers(person)).json()["campaigns"]}
        assert after == before
        people = [row for row in _rows(server.get("/v1/person", params={"limit": 500}, headers=_headers(person)).json()) if row["name"] == "Captain Vell"]
        assert sorted(row["campaign_id"] for row in people) == sorted([scenario["id"], first["id"]])


class TestStartingFast:
    """Zephyrex RPG, 2026-11-21: Voidship (224 records) took 45 s to start. A start is a handful of
    plural creates, so a scenario of 120 records, each with a property and a picture, starts in a
    few seconds."""

    @pytest.mark.usefixtures("memory_store")
    def test_a_large_scenario_starts_in_seconds(self, server: TestClient, person: Any) -> None:
        import time

        scenario = _create(server, person, "campaign", name="Big Ship", is_scenario=True)
        asset = server.post("/v1/asset/upload", params={"name": "face.png"}, content=b"\x89PNG face", headers={**_headers(person), "Content-Type": "image/png"}).json()["asset"]
        crew: list[dict[str, Any]] = []
        # 120 people: more than one plural create (at most 100), so the start's creates chunk too.
        for first in (0, 60):
            made = server.post(
                "/v1/person",
                json={"persons": [{"name": f"Crew {number}", "kind": "npc", "campaign_id": scenario["id"]} for number in range(first, first + 60)]},
                headers=_headers(person),
            )
            assert made.status_code in (200, 201), made.text
            crew.extend(next(value for value in made.json().values() if isinstance(value, list)))
        for one in crew:
            server.post("/v1/record_metadata", json={"record_metadata": {"target_entity_type": "person", "target_entity_id": one["id"], "key": "Vault path", "value": f"Crew/{one['name']}.md", "is_private": True}}, headers=_headers(person))
            server.post("/v1/attachment", json={"attachment": {"asset_id": asset["id"], "target_entity_type": "person", "target_entity_id": one["id"], "role": "primary_image"}}, headers=_headers(person))

        started = time.monotonic()
        _run, ids = _started(server, person, _start(server, person, scenario["id"]))
        took = time.monotonic() - started
        assert len(ids) >= 121
        # About 8 s on the runner; 45 s for 224 records before (one write per property and picture).
        assert took < 15, f"the start took {took:.1f} s: {_STEPS_SEEN}"


class TestEnsurePerson:
    """Parity, 2026-11-21 (play-test): a narrator's unnamed NPC who speaks joins the cast, made once,
    GM only, marked as made in play; the campaign's GM's to do."""

    def test_made_once_gm_only_and_only_by_the_gm(self, server: TestClient, person: Any, other: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        campaign = _create(server, person, "campaign", name="The Rusty Anchor")
        made = server.post(f"/v1/campaign/{campaign['id']}/person", json={"person": {"name": "The Barkeep", "summary": "Pours, listens."}}, headers=_headers(person))
        assert made.status_code == 200, made.text
        barkeep = made.json()["person"]
        assert (barkeep["name"], barkeep["created"]) == ("The Barkeep", True)
        row = server.get(f"/v1/person/{barkeep['id']}", headers=_headers(person)).json()["person"]
        assert (row["kind"], row["campaign_id"], row["provenance"]) == ("npc", campaign["id"], "homebrew")
        assert "Pours, listens." in row["entry"]
        properties = server.get("/v1/record_metadata/of", params={"target_entity_type": "person", "target_entity_id": barkeep["id"]}, headers=_headers(person)).json()["metadata"]
        assert {(one["key"], one["value"], one["is_private"]) for one in properties} == {("GM only", "true", True), ("Made in play", "By the narrator", True)}
        # The same name again, case aside: the same person, nothing made.
        again = server.post(f"/v1/campaign/{campaign['id']}/person", json={"person": {"name": "the barkeep"}}, headers=_headers(person)).json()["person"]
        assert again == {"id": barkeep["id"], "name": "The Barkeep", "created": False}
        # Through the ability rpg-ai calls in process.
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        ensure = loaded_ability(registry, "rpg_core", "ensure_person")
        assert ensure is not None
        assert ensure(registry, str(person.id), campaign["id"], "THE BARKEEP")["id"] == barkeep["id"]
        stranger = ensure(registry, str(person.id), campaign["id"], "A Hooded Stranger", None)
        assert stranger["created"] is True and stranger["id"] != barkeep["id"]
        # Someone else's campaign: not theirs to read, so not found.
        refused = server.post(f"/v1/campaign/{campaign['id']}/person", json={"person": {"name": "Intruder"}}, headers=_headers(other))
        assert refused.status_code == 404, refused.text
        names = sorted(one["name"] for one in _rows(server.get(f"/v1/person?campaign_id={campaign['id']}", headers=_headers(person)).json()))
        assert names == ["A Hooded Stranger", "The Barkeep"]


class TestPregens:
    """Operator, 2026-11-21: setting-wide characters to pick from at a start, a couple per class."""

    def test_listed_by_setting_and_copied_in_on_start(self, server: TestClient, person: Any) -> None:
        setting = _create(server, person, "setting", name="Pregen Setting")
        akra = _create(server, person, "person", name="Akra (Dragonborn Cleric, 2014)", kind="pc", setting_id=setting["id"],
                       entry=[{"type": "p", "children": [{"text": "Level 1 Dragonborn Cleric."}]}, {"type": "p", "children": [{"text": "Devout."}]}])
        plain = _create(server, person, "person", name="Not a pregen", kind="pc", setting_id=setting["id"])
        pregen = _create(server, person, "taxon", name="Pregen", kind="category", setting_id=setting["id"])
        cleric = _create(server, person, "taxon", name="Cleric", kind="category", setting_id=setting["id"])
        for taxon in (pregen, cleric):
            _create(server, person, "entity_taxon", taxon_id=taxon["id"], target_entity_type="person", target_entity_id=akra["id"])

        listed = server.get(f"/v1/setting/{setting['id']}/pregen", headers=_headers(person))
        assert listed.status_code == 200, listed.text
        assert listed.json()["pregens"] == [
            {"id": akra["id"], "name": "Akra (Dragonborn Cleric, 2014)", "summary": "Level 1 Dragonborn Cleric.", "picture_url": None, "tags": ["Pregen", "Cleric"], "source": None}
        ]

        # Operator, 2026-11-22: "The inventory and character sheets of prefab characters should all be
        # done already at start". What a pregen carries comes with it (its sheet is VTT's, copied by
        # VTT's AFTER_INSTANTIATE through the same id map).
        kit = []
        for name in ("Mace", "Holy symbol"):
            item = _create(server, person, "item", name=name, kind="misc", setting_id=setting["id"])
            instance = _create(server, person, "item_instance", item_id=item["id"], owner_person_id=akra["id"])
            _create(server, person, "entity_inventory", item_instance_id=instance["id"], target_entity_type="person", target_entity_id=akra["id"])
            kit.append((item, instance))

        scenario = _create(server, person, "campaign", name="Pregen Scenario", setting_id=setting["id"], is_scenario=True)
        refused = server.post(f"/v1/campaign/{scenario['id']}/instantiate", json={"instantiate": {"pregens": [plain["id"]]}}, headers=_headers(person))
        assert refused.status_code == 422, refused.text
        run, ids = _started(server, person, _start_with(server, person, scenario["id"], [akra["id"]]))
        copy = server.get(f"/v1/person/{ids[akra['id']]}", headers=_headers(person)).json()["person"]
        assert (copy["name"], copy["campaign_id"], copy["kind"]) == ("Akra (Dragonborn Cleric, 2014)", run["id"], "pc")
        copied_tags = {row["taxon_id"] for row in server.get(f"/v1/entity_taxon?target_entity_type=person&target_entity_id={copy['id']}", headers=_headers(person)).json()["entity_taxons"]}
        assert copied_tags == {pregen["id"], cleric["id"]}
        # Its kit: both items carried by the copy, each a new instance it owns, of the same item.
        carried = server.get(f"/v1/entity_inventory?target_entity_type=person&target_entity_id={copy['id']}", headers=_headers(person)).json()["entity_inventories"]
        assert len(carried) == 2
        instances = [server.get(f"/v1/item_instance/{row['item_instance_id']}", headers=_headers(person)).json()["item_instance"] for row in carried]
        assert sorted(one["item_id"] for one in instances) == sorted(item["id"] for item, _instance in kit)
        assert {one["owner_person_id"] for one in instances} == {copy["id"]} and not {one["id"] for one in instances} & {instance["id"] for _item, instance in kit}
        held = server.get(f"/v1/entity_inventory?target_entity_type=person&target_entity_id={akra['id']}", headers=_headers(person)).json()["entity_inventories"]
        assert len(held) == 2
        # The setting's own is untouched, and still listed.
        original = server.get(f"/v1/person/{akra['id']}", headers=_headers(person)).json()["person"]
        assert original["campaign_id"] is None
        assert [one["id"] for one in server.get(f"/v1/setting/{setting['id']}/pregen", headers=_headers(person)).json()["pregens"]] == [akra["id"]]


class TestAfterInstantiate:
    """VTT, 2026-11-21: once a playthrough is made, other extensions copy what's theirs (scenes and
    tokens) through AFTER_INSTANTIATE; one that fails doesn't undo the start."""

    def test_callbacks_get_the_id_map_and_a_failing_one_is_passed_over(self, server: TestClient, person: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        from zephyrex.extensions.rpg_core import BLL_RPGCore  # type: ignore[import-not-found]

        heard: list[tuple[str, str, str, dict[str, str]]] = []

        def broken(*_args: Any) -> None:
            raise RuntimeError("the VTT's copy failed")

        def listening(_registry: Any, requester_id: str, source_id: str, new_id: str, id_map: dict[str, str]) -> None:
            heard.append((requester_id, source_id, new_id, id_map))

        monkeypatch.setattr(BLL_RPGCore, "AFTER_INSTANTIATE", [broken, listening])
        scenario = _create(server, person, "campaign", name="Mapped", is_scenario=True)
        inn = _create(server, person, "location", name="The Inn", kind="building", campaign_id=scenario["id"])
        run, ids = _started(server, person, _start(server, person, scenario["id"]))
        assert len(heard) == 1
        requester_id, source_id, new_id, id_map = heard[0]
        assert (requester_id, source_id, new_id) == (str(person.id), scenario["id"], run["id"])
        assert id_map[inn["id"]] == ids[inn["id"]]


class TestOptionalExtensions:
    """VTT, 2026-11-21: an app can name an extension whose models it never registered; rpg_core reads
    one only when its model is there, so a start doesn't fail on it."""

    def test_an_extension_named_but_not_registered_is_not_served(self, server: TestClient) -> None:
        from zephyrex.extensions.rpg_core.BLL_RPGCore import _serves  # type: ignore[import-not-found]

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        assert _serves(registry, "metadata") and _serves(registry, "attachments")

        class NamedOnly:
            def loaded_extension_names(self) -> frozenset[str]:
                return frozenset({"metadata", "attachments"})

            def apply(self, model: Any) -> Any:
                raise TypeError(f"No matching type found in registry for {model.__name__}!")

        class NotNamed:
            def loaded_extension_names(self) -> frozenset[str]:
                return frozenset()

        assert not _serves(NamedOnly(), "metadata") and not _serves(NamedOnly(), "attachments")
        assert not _serves(NotNamed(), "metadata")


class TestCampaignFraming:
    """Parity, 2026-11-22: the narrator's frame from the wiki campaign itself (vault_import put each
    scenario's framing there): description, framing, GM notes for the GM, setting tone, play styles."""

    def test_framing_split_and_the_scenario_fallback(self, server: TestClient, person: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        setting = _create(server, person, "setting", name="Framed Setting", entry=[{"type": "p", "children": [{"text": "Grim and gothic."}]}])
        scenario = _create(server, person, "campaign", name="Behind the Lines", setting_id=setting["id"], is_scenario=True, description="A recon squad behind Ork lines.")
        _create(
            server, person, "journal", name="Behind the Lines: Campaign Framing", kind="campaign_framing", campaign_id=scenario["id"],
            entry=[
                {"type": "h1", "children": [{"text": "Behind the Lines: Campaign Framing"}]},
                {"type": "h2", "children": [{"text": "Premise"}]},
                {"type": "p", "children": [{"text": "Scout the manufactorum."}]},
                {"type": "h2", "children": [{"text": "GM Notes"}]},
                {"type": "p", "children": [{"text": "The Orks are building a gargant."}]},
            ],
        )
        style = _create(server, person, "taxon", name="Exploration", kind="play_style")
        _create(server, person, "entity_taxon", taxon_id=style["id"], target_entity_type="campaign", target_entity_id=scenario["id"])

        got = server.get(f"/v1/campaign/{scenario['id']}/framing", headers=_headers(person))
        assert got.status_code == 200, got.text
        assert got.json()["campaign_framing"] == {
            "campaign_id": scenario["id"],
            "name": "Behind the Lines",
            "description": "A recon squad behind Ork lines.",
            "framing": "Premise\nScout the manufactorum.",
            "gm_notes": "GM Notes\nThe Orks are building a gargant.",
            "setting": {"id": setting["id"], "name": "Framed Setting", "tone": "Grim and gothic."},
            "play_styles": ["Exploration"],
            "from_scenario": False,
            # The wiki alone serves no game systems (zephyrex-vtt's).
            "game_system": None,
        }
        # A playthrough with nothing of its own takes its scenario's.
        bare = _create(server, person, "campaign", name="Run, bare", setting_id=setting["id"], scenario_id=scenario["id"])
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        framing = loaded_ability(registry, "rpg_core", "campaign_framing")
        assert framing is not None
        fallback = framing(registry, str(person.id), bare["id"])["campaign_framing"]
        assert (fallback["framing"], fallback["play_styles"], fallback["from_scenario"]) == ("Premise\nScout the manufactorum.", ["Exploration"], True)
        # Anyone but the GM gets no GM notes.
        import zephyrex.lib.RecordTarget as target

        monkeypatch.setattr(target, "can_edit", lambda *_args: False)
        assert framing(registry, str(person.id), scenario["id"])["campaign_framing"]["gm_notes"] == ""

        # A served game system (zephyrex-vtt's, through the framework's record lookup) reads as
        # {id, slug, name} (operator, 2026-11-25: "The decision model prompts are mentioning vox in
        # DnD campaigns"); none set, none served or not visible is none.
        from types import SimpleNamespace

        from fastapi import HTTPException
        from zephyrex.extensions.rpg_core import BLL_RPGCore  # type: ignore[import-not-found]

        class Systems:
            def __init__(self, requester_id: str, model_registry: Any) -> None:
                pass

            def get(self, id: str) -> Any:
                if id != "gs1":
                    raise HTTPException(status_code=404, detail="GameSystemModel not found")
                return SimpleNamespace(id=id, slug="srd-5e", name="D&D 5e (SRD)")

        monkeypatch.setattr(target, "record_manager", lambda _registry, kind: Systems)
        assert BLL_RPGCore._game_system_of(registry, str(person.id), "gs1") == BLL_RPGCore.FramingSystem(id="gs1", slug="srd-5e", name="D&D 5e (SRD)")
        assert BLL_RPGCore._game_system_of(registry, str(person.id), "gone") is None
        assert BLL_RPGCore._game_system_of(registry, str(person.id), None) is None


class TestDeletingACampaign:
    """Zephyrex RPG, 2026-11-22: deleted playthroughs left their records behind. A campaign deleted
    takes its records along; remove_orphaned_records clears those left by earlier deletes."""

    @staticmethod
    def _furnished(server: TestClient, person: Any, name: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        campaign = _create(server, person, "campaign", name=name)
        inn = _create(server, person, "location", name=f"{name} Inn", kind="building", campaign_id=campaign["id"])
        keeper = _create(server, person, "person", name=f"{name} Keeper", kind="npc", campaign_id=campaign["id"], location_id=inn["id"])
        tag = _create(server, person, "taxon", name=f"{name} Tag", kind="tag", campaign_id=campaign["id"])
        _create(server, person, "entity_taxon", taxon_id=tag["id"], target_entity_type="person", target_entity_id=keeper["id"])
        added = server.post(
            "/v1/record_metadata",
            json={"record_metadata": {"target_entity_type": "person", "target_entity_id": keeper["id"], "key": "Mood", "value": "dour"}},
            headers=_headers(person),
        )
        assert added.status_code == 201, added.text
        return campaign, inn, keeper

    def test_a_deleted_campaign_takes_its_records_and_orphans_are_cleared(self, server: TestClient, person: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability
        from zephyrex.extensions.rpg_core import BLL_RPGCore  # type: ignore[import-not-found]

        kept, kept_inn, _kept_keeper = self._furnished(server, person, "Kept")
        gone, inn, keeper = self._furnished(server, person, "Gone")
        assert _delete(server, person, "campaign", gone["id"]).status_code in (200, 204)
        assert server.get(f"/v1/person/{keeper['id']}", headers=_headers(person)).status_code == 404
        assert server.get(f"/v1/location/{inn['id']}", headers=_headers(person)).status_code == 404
        assert server.get(f"/v1/entity_taxon?target_entity_type=person&target_entity_id={keeper['id']}", headers=_headers(person)).json()["entity_taxons"] == []
        # Another campaign's records stay.
        assert server.get(f"/v1/location/{kept_inn['id']}", headers=_headers(person)).status_code == 200

        # A campaign deleted before deleting took records along: its orphans, cleared by the ability.
        monkeypatch.setattr(BLL_RPGCore, "CASCADE_ON_DELETE", False)
        old, old_inn, old_keeper = self._furnished(server, person, "Old")
        assert _delete(server, person, "campaign", old["id"]).status_code in (200, 204)
        assert server.get(f"/v1/person/{old_keeper['id']}", headers=_headers(person)).status_code == 200
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        clear = loaded_ability(registry, "rpg_core", "remove_orphaned_records")
        assert clear is not None
        # A dry run says what would go and deletes nothing.
        planned = clear(registry, str(person.id), dry_run=True)
        assert planned["campaigns"] == [old["id"]] and planned["removed"]["person"] == 1
        assert server.get(f"/v1/person/{old_keeper['id']}", headers=_headers(person)).status_code == 200
        result = clear(registry, str(person.id))
        assert result == planned
        assert result["removed"]["person"] == 1 and result["removed"]["location"] == 1 and result["removed"]["property"] == 1
        assert server.get(f"/v1/person/{old_keeper['id']}", headers=_headers(person)).status_code == 404
        assert server.get(f"/v1/location/{kept_inn['id']}", headers=_headers(person)).status_code == 200
        assert clear(registry, str(person.id)) == {"campaigns": [], "removed": {}}


class TestAuthoredNpcs:
    """Operator, 2026-11-22: the GM authors NPCs mid-play (filled in by an agent), campaign-only,
    with "elevate to scenario" so later playthroughs have them."""

    def test_an_npc_filled_in_by_an_agent(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        campaign = _create(server, person, "campaign", name="Filled")
        barkeep = server.post(f"/v1/campaign/{campaign['id']}/person", json={"person": {"name": "The Barkeep"}}, headers=_headers(person)).json()["person"]
        filled = server.post(
            f"/v1/campaign/{campaign['id']}/fill_person",
            json={"person": {"person_id": barkeep["id"], "summary": "Keeps the Rusty Anchor.", "entry": "## Personality\nGruff.", "personality": "Gruff but fair", "motive": "Pay the Guild", "voice": "Short sentences", "picture": "https://example.org/barkeep.png"}},
            headers=_headers(person),
        )
        assert filled.status_code == 200, filled.text
        assert filled.json()["person"]["updated"] == ["entry", "motive", "personality", "picture", "summary", "voice"]
        row = server.get(f"/v1/person/{barkeep['id']}", headers=_headers(person)).json()["person"]
        assert "Keeps the Rusty Anchor." in row["entry"] and "Personality" in row["entry"]
        assert json.loads(row["voice"])["personality"] == "Gruff but fair" and json.loads(row["voice"])["speech"] == "Short sentences"
        assert json.loads(row["motivations"]) == ["Pay the Guild"] and row["picture_url"] == "https://example.org/barkeep.png"
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        update = loaded_ability(registry, "rpg_core", "update_person")
        assert update is not None
        with pytest.raises(Exception, match="not mood"):
            update(registry, str(person.id), barkeep["id"], {"mood": "dour"})
        with pytest.raises(Exception, match="Upload the picture first"):
            update(registry, str(person.id), barkeep["id"], {"picture": "data:image/png;base64,AAAA"})

    def test_elevated_to_the_scenario_with_its_place_ties_tags_and_properties(self, server: TestClient, person: Any) -> None:
        scenario = _create(server, person, "campaign", name="Anchor Scenario", is_scenario=True)
        inn = _create(server, person, "location", name="The Rusty Anchor", kind="building", campaign_id=scenario["id"])
        guild = _create(server, person, "faction", name="Dockers' Guild", kind="guild", campaign_id=scenario["id"])
        run = _create(server, person, "campaign", name="Anchor, run 1", scenario_id=scenario["id"])
        run_inn = _create(server, person, "location", name="The Rusty Anchor", kind="building", campaign_id=run["id"])
        run_guild = _create(server, person, "faction", name="Dockers' Guild", kind="guild", campaign_id=run["id"])
        barkeep = _create(server, person, "person", name="Old Tam", kind="npc", campaign_id=run["id"], location_id=run_inn["id"])
        _create(server, person, "relationship", person_id=barkeep["id"], target_faction_id=run_guild["id"], kind="member")
        tag = _create(server, person, "taxon", name="Regulars", kind="tag", campaign_id=run["id"])
        _create(server, person, "entity_taxon", taxon_id=tag["id"], target_entity_type="person", target_entity_id=barkeep["id"])
        server.post("/v1/record_metadata", json={"record_metadata": {"target_entity_type": "person", "target_entity_id": barkeep["id"], "key": "Mood", "value": "dour"}}, headers=_headers(person))

        lifted = server.post(f"/v1/campaign/{run['id']}/elevate", json={"elevate": {"person_id": barkeep["id"]}}, headers=_headers(person))
        assert lifted.status_code == 200, lifted.text
        elevated = lifted.json()["elevated"]
        assert (elevated["scenario_id"], elevated["created"]) == (scenario["id"], True)
        twin = server.get(f"/v1/person/{elevated['scenario_person_id']}", headers=_headers(person)).json()["person"]
        assert (twin["name"], twin["campaign_id"], twin["location_id"]) == ("Old Tam", scenario["id"], inn["id"])
        ties = server.get(f"/v1/relationship?person_id={twin['id']}", headers=_headers(person)).json()["relationships"]
        assert [tie["target_faction_id"] for tie in ties] == [guild["id"]]
        tagged = server.get(f"/v1/entity_taxon?target_entity_type=person&target_entity_id={twin['id']}", headers=_headers(person)).json()["entity_taxons"]
        scenario_tag = server.get(f"/v1/taxon/{tagged[0]['taxon_id']}", headers=_headers(person)).json()["taxon"]
        assert (scenario_tag["name"], scenario_tag["campaign_id"]) == ("Regulars", scenario["id"])
        props = {row["key"]: row["value"] for row in server.get("/v1/record_metadata/of", params={"target_entity_type": "person", "target_entity_id": twin["id"]}, headers=_headers(person)).json()["metadata"]}
        assert props == {"Mood": "dour"}
        marks = {row["key"]: row["value"] for row in server.get("/v1/record_metadata/of", params={"target_entity_type": "person", "target_entity_id": barkeep["id"]}, headers=_headers(person)).json()["metadata"]}
        assert marks["Elevated to"] == twin["id"]
        # Again: nothing new, the same counterpart.
        again = server.post(f"/v1/campaign/{run['id']}/elevate", json={"elevate": {"person_id": barkeep["id"]}}, headers=_headers(person)).json()["elevated"]
        assert (again["scenario_person_id"], again["created"]) == (twin["id"], False)
        # Not a playthrough: nothing to elevate to.
        loose = _create(server, person, "campaign", name="Loose")
        stray = _create(server, person, "person", name="Stray", kind="npc", campaign_id=loose["id"])
        assert server.post(f"/v1/campaign/{loose['id']}/elevate", json={"elevate": {"person_id": stray["id"]}}, headers=_headers(person)).status_code == 422


class TestRelevanceRead:
    """Operator, 2026-11-22: "Why is it reading the whole world instead of tag/relevance based
    injection?" A turn reads only the records its text names, through the key index."""

    def test_only_what_the_text_names_from_campaign_and_canon(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability
        from zephyrex.extensions.rpg_core import BLL_RPGCore  # type: ignore[import-not-found]

        setting = _create(server, person, "setting", name="Relevance Setting")
        campaign = _create(server, person, "campaign", name="Relevance", setting_id=setting["id"])
        other = _create(server, person, "campaign", name="Elsewhere", setting_id=setting["id"])
        tam = _create(server, person, "person", name="Old Tam", kind="npc", campaign_id=campaign["id"], aliases=["the Barkeep"])
        inn = _create(server, person, "location", name="The Rusty Anchor", kind="building", campaign_id=campaign["id"])
        _create(server, person, "person", name="Silent Sal", kind="npc", campaign_id=campaign["id"])
        lantern = _create(server, person, "item", name="Storm Lantern", kind="misc", setting_id=setting["id"])
        _create(server, person, "item", name="Unread Tome", kind="misc", setting_id=setting["id"])
        oath = _create(server, person, "journal", name="The Oath", kind="lore", campaign_id=campaign["id"], lore={"always_active": True})
        _create(server, person, "person", name="Old Tam", kind="npc", campaign_id=other["id"])

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        matching = loaded_ability(registry, "rpg_core", "world_entities_matching")
        assert matching is not None
        got = matching(registry, str(person.id), campaign["id"], "The barkeep lights a storm lantern at the Rusty Anchor.")
        found = {entity["id"]: entity["name"] for entity in got["world_entities"]}
        # Named (by alias, any case, the canon's lantern), and the always-active oath; not Sal, not the
        # tome, not the other campaign's Tam.
        assert set(found) == {tam["id"], inn["id"], lantern["id"], oath["id"]}
        assert got["matched"][tam["id"]] == ["the barkeep"] and got["matched"][oath["id"]] == ["*"]
        # Without the setting's canon, the lantern goes.
        own = matching(registry, str(person.id), campaign["id"], "the storm lantern", include_setting=False)
        assert [entity["id"] for entity in own["world_entities"]] == [oath["id"]]
        # A renamed record's keys follow it.
        current = server.get(f"/v1/person/{tam['id']}", headers=_headers(person))
        renamed = server.put(f"/v1/person/{tam['id']}", json={"person": {"name": "Tamwell"}}, headers=_headers(person, **{"If-Match": current.headers["ETag"]}))
        assert renamed.status_code == 200, renamed.text
        assert tam["id"] not in {entity["id"] for entity in matching(registry, str(person.id), campaign["id"], "Old Tam waves")["world_entities"]}
        assert tam["id"] in {entity["id"] for entity in matching(registry, str(person.id), campaign["id"], "Tamwell nods")["world_entities"]}
        # Tags narrow it; the REST twin answers the same.
        tag = _create(server, person, "taxon", name="Locals", kind="tag", campaign_id=campaign["id"])
        _create(server, person, "entity_taxon", taxon_id=tag["id"], target_entity_type="location", target_entity_id=inn["id"])
        posted = server.post(f"/v1/campaign/{campaign['id']}/matching", json={"matching": {"text": "the Rusty Anchor and the storm lantern", "tags": ["locals"]}}, headers=_headers(person))
        assert posted.status_code == 200, posted.text
        assert [entity["id"] for entity in posted.json()["world_entities"]] == [inn["id"]]
        # Records whose keys are lost (made before the index) come back with the rebuild.
        keys = BLL_RPGCore.WorldKeyManager(requester_id=__import__("zephyrex.lib.Environment", fromlist=["env"]).env("SYSTEM_ID"), model_registry=registry)
        for row in keys.list(target_entity_id=inn["id"]) or []:
            keys.delete(id=str(row.id))
        assert inn["id"] not in {entity["id"] for entity in matching(registry, str(person.id), campaign["id"], "the Rusty Anchor")["world_entities"]}
        rebuilt = loaded_ability(registry, "rpg_core", "rebuild_world_keys")(registry, str(person.id))
        assert rebuilt["location"] >= 1
        assert inn["id"] in {entity["id"] for entity in matching(registry, str(person.id), campaign["id"], "the Rusty Anchor")["world_entities"]}


class TestWhereTheyAre:
    """Parity: who's present in a scene is who's at its place or inside it."""

    def test_a_persons_place_and_a_places_parent_reach_the_sync(self, server: TestClient, person: Any) -> None:
        campaign = _create(server, person, "campaign", name="Present")
        shrine = _create(server, person, "location", name="The Engine Shrine", kind="building", campaign_id=campaign["id"])
        crypt = _create(server, person, "location", name="Crypt", kind="room", campaign_id=campaign["id"], parent_id=shrine["id"])
        calloway = _create(server, person, "person", name="Calloway", kind="npc", campaign_id=campaign["id"], location_id=crypt["id"])
        synced = {row["name"]: row for row in server.get(f"/v1/world_entity?ids={calloway['id']},{crypt['id']},{shrine['id']}", headers=_headers(person)).json()["world_entities"]}
        assert (synced["Calloway"]["location_id"], synced["Crypt"]["parent_id"], synced["The Engine Shrine"]["parent_id"]) == (crypt["id"], shrine["id"], None)
        assert (synced["Calloway"]["parent_id"], synced["Crypt"]["location_id"]) == (None, None)


class TestCampaignDocuments:
    """Parity's data bank: each of a campaign's records' full text, journals first, GM-only marked;
    and the three abilities rpg-ai calls in process."""

    def test_documents_by_route_and_ability(self, server: TestClient, person: Any, other: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        campaign = _create(server, person, "campaign", name="Documented")
        truth = _create(server, person, "journal", name="The Truth", kind="lore", campaign_id=campaign["id"], entry=[{"type": "p", "children": [{"text": "The keeper is the thief."}]}])
        _create(server, person, "person", name="Mira", kind="npc", campaign_id=campaign["id"], entry=[{"type": "p", "children": [{"text": "Keeps the light."}]}])
        _create(server, person, "location", name="Empty", kind="room", campaign_id=campaign["id"])
        _create(server, person, "person", name="Mould", kind="npc", campaign_id=campaign["id"], is_template=True, entry=[{"type": "p", "children": [{"text": "A template."}]}])
        added = server.post(
            "/v1/record_metadata",
            json={"record_metadata": {"target_entity_type": "journal", "target_entity_id": truth["id"], "key": "GM only", "value": "true", "value_type": "boolean", "is_private": True}},
            headers=_headers(person),
        )
        assert added.status_code == 201, added.text
        response = server.get(f"/v1/campaign_document?campaign_id={campaign['id']}", headers=_headers(person))
        assert response.status_code == 200, response.text
        documents = response.json()["campaign_documents"]
        assert [(one["kind"], one["name"], one["text"], one["gm_only"]) for one in documents] == [
            ("journal", "The Truth", "The keeper is the thief.", True),
            ("person", "Mira", "Keeps the light.", False),
        ]
        assert server.get(f"/v1/campaign_document?campaign_id={campaign['id']}", headers=_headers(other)).status_code == 404

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        by_ability = loaded_ability(registry, "rpg_core", "campaign_documents")(registry, str(person.id), campaign["id"])
        assert [one["name"] for one in by_ability["campaign_documents"]] == ["The Truth", "Mira"]
        cast = loaded_ability(registry, "rpg_core", "world_entities_by_id")(registry, str(person.id), [truth["id"]])
        assert [one["name"] for one in cast["world_entities"]] == ["The Truth"]
        started = loaded_ability(registry, "rpg_core", "instantiate_campaign")(registry, str(person.id), campaign["id"], "Run")
        assert started["campaign"]["scenario_id"] == campaign["id"] and truth["id"] in started["id_map"]


class TestWorldTick:
    """The GM side pilots people by their routine and motivations as the campaign's clock advances."""

    def test_routine_motivations_clock_and_moves(self, server: TestClient, person: Any, other: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        setting = _create(server, person, "setting", name="Tick Setting")
        campaign = _create(server, person, "campaign", name="Ticking", setting_id=setting["id"])
        forge = _create(server, person, "location", name="Forge", kind="building", campaign_id=campaign["id"])
        home = _create(server, person, "location", name="Home", kind="building", campaign_id=campaign["id"])
        shrine = _create(server, person, "location", name="Canon shrine", kind="building", setting_id=setting["id"])
        elsewhere = _create(server, person, "location", name="Elsewhere", kind="building", campaign_id=_create(server, person, "campaign", name="Other")["id"])
        routine = [{"from": "18:00", "to": "06:00", "location_id": home["id"], "activity": "Sleeps"}, {"from": "08:00", "to": "17:00", "days": [4, 0], "location_id": forge["id"], "activity": "Works"}]
        smith = _create(server, person, "person", name="Smith", kind="npc", campaign_id=campaign["id"], location_id=home["id"], routine=routine, motivations=[" Pay the debt ", "Pay the debt"])
        [synced] = server.get(f"/v1/world_entity?ids={smith['id']}", headers=_headers(person)).json()["world_entities"]
        assert [slot["from"] for slot in synced["routine"]] == ["08:00", "18:00"] and synced["routine"][0]["days"] == [0, 4]
        assert synced["motivations"] == ["Pay the debt"]
        assert server.post("/v1/person", json={"person": {"name": "Bad", "routine": [{"from": "8am", "to": "9"}]}}, headers=_headers(person)).status_code == 422

        # The clock: day 1, 08:00 to start; advanced by its GM; no one else's to advance.
        assert server.get(f"/v1/campaign/{campaign['id']}/clock", headers=_headers(person)).json() == {"minutes": 480, "day": 1, "time": "08:00", "reason": None}
        advanced = server.post(f"/v1/campaign/{campaign['id']}/clock", json={"clock": {"minutes": 1440 + 90, "reason": "A day's travel"}}, headers=_headers(person))
        assert advanced.status_code == 200, advanced.text
        assert advanced.json() == {"minutes": 2010, "day": 2, "time": "09:30", "reason": "A day's travel"}
        assert server.post(f"/v1/campaign/{campaign['id']}/clock", json={"clock": {"minutes": 0}}, headers=_headers(person)).status_code == 422
        assert server.post(f"/v1/campaign/{campaign['id']}/clock", json={"clock": {"minutes": 5}}, headers=_headers(other)).status_code == 404

        # Moves: within the campaign or its setting's canon, recorded with where from and when.
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        moved = loaded_ability(registry, "rpg_core", "move_person")(registry, str(person.id), smith["id"], forge["id"], "Work starts")
        assert (moved["from"], moved["to"], moved["at"]["time"], moved["reason"]) == (home["id"], forge["id"], "09:30", "Work starts")
        assert server.get(f"/v1/person/{smith['id']}", headers=_headers(person)).json()["person"]["location_id"] == forge["id"]
        canon = server.post("/v1/person_move", json={"person_move": {"person_id": smith["id"], "to_location_id": shrine["id"], "reason": "Prayer"}}, headers=_headers(person))
        assert canon.status_code == 201, canon.text
        refused = server.post("/v1/person_move", json={"person_move": {"person_id": smith["id"], "to_location_id": elsewhere["id"]}}, headers=_headers(person))
        assert refused.status_code == 422, refused.text
        history = server.get(f"/v1/person_move?person_id={smith['id']}", headers=_headers(person)).json()["person_moves"]
        assert sorted((row["from_location_id"], row["to_location_id"]) for row in history) == sorted([(home["id"], forge["id"]), (forge["id"], shrine["id"])])
        clock_now = loaded_ability(registry, "rpg_core", "campaign_clock")(registry, str(person.id), campaign["id"])
        assert (clock_now["day"], clock_now["time"]) == (2, "09:30")
        later = loaded_ability(registry, "rpg_core", "advance_clock")(registry, str(person.id), campaign["id"], 30, "Prayers")
        assert later["time"] == "10:00"


class TestPartyKnowsItself:
    """Parity's party fix: tag names on every record, and a person's ties to other people (a tie with
    a GM-only end left out)."""

    def test_tags_and_ties_reach_the_sync(self, server: TestClient, person: Any) -> None:
        campaign = _create(server, person, "campaign", name="Party")
        pc = _create(server, person, "taxon", name="PC", kind="tag", campaign_id=campaign["id"])
        ilsa = _create(server, person, "person", name="Ilsa", kind="pc", campaign_id=campaign["id"])
        vex = _create(server, person, "person", name="Vex", kind="pc", campaign_id=campaign["id"])
        spy = _create(server, person, "person", name="The spy", kind="npc", campaign_id=campaign["id"])
        for one in (ilsa, vex):
            _create(server, person, "entity_taxon", taxon_id=pc["id"], target_entity_type="person", target_entity_id=one["id"])
        _create(server, person, "relationship", person_id=ilsa["id"], target_person_id=vex["id"], kind="friend", intensity=0.8, notes="He pulled her out of the hive fire.")
        _create(server, person, "relationship", person_id=ilsa["id"], target_person_id=spy["id"], kind="ally", intensity=0.2)
        secret = server.post(
            "/v1/record_metadata",
            json={"record_metadata": {"target_entity_type": "person", "target_entity_id": spy["id"], "key": "GM only", "value": "true", "value_type": "boolean", "is_private": True}},
            headers=_headers(person),
        )
        assert secret.status_code == 201, secret.text
        synced = {row["name"]: row for row in server.get(f"/v1/world_entity?campaign_id={campaign['id']}", headers=_headers(person)).json()["world_entities"]}
        assert (synced["Ilsa"]["tags"], synced["Vex"]["tags"], synced["The spy"]["tags"]) == (["PC"], ["PC"], [])
        assert synced["Ilsa"]["relationships"] == [{"to_id": vex["id"], "kind": "friend", "note": "He pulled her out of the hive fire."}]
        assert synced["Vex"]["relationships"] == []
        by_id = server.get(f"/v1/world_entity?ids={ilsa['id']}", headers=_headers(person)).json()["world_entities"][0]
        assert by_id["relationships"] == synced["Ilsa"]["relationships"]


class TestLoreSearch:
    """Hybrid retrieval (operator, 2026-11-22; design approved): a campaign's passages for a text,
    the records it names first, then the other ranks fused, kept to its scope and a token budget.
    Postgres's full-text, trigram and vector parts are first exercised on prod (operator: "Skip PG
    tests for now"); here SQLite answers with the basic text rank and says so."""

    ENTRY = [
        {"type": "p", "children": [{"text": "Keeps the Rusty Anchor."}]},
        {"type": "h2", "children": [{"text": "Motive"}]},
        {"type": "p", "children": [{"text": "Pay the Guild before winter comes."}]},
    ]

    def test_passages_in_scope_named_first_then_by_text(self, server: TestClient, person: Any, other: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        setting = _create(server, person, "setting", name="Lore Setting")
        elsewhere = _create(server, person, "setting", name="Elsewhere Setting")
        campaign = _create(server, person, "campaign", name="Lore Campaign", setting_id=setting["id"])
        sibling = _create(server, person, "campaign", name="Lore Sibling", setting_id=setting["id"])
        tam = _create(server, person, "person", name="Old Tam", kind="npc", campaign_id=campaign["id"], entry=self.ENTRY)
        guild = _create(server, person, "faction", name="The Coin Guild", campaign_id=campaign["id"],
                        entry=[{"type": "p", "children": [{"text": "Lends at winter rates to desperate innkeepers."}]}])
        canon = _create(server, person, "item", name="Storm Lantern", kind="misc", setting_id=setting["id"],
                        entry=[{"type": "p", "children": [{"text": "Burns through any winter gale."}]}])
        _create(server, person, "item", name="Far Lantern", kind="misc", setting_id=elsewhere["id"],
                entry=[{"type": "p", "children": [{"text": "A winter lamp of another world."}]}])
        _create(server, person, "person", name="Sibling Sal", kind="npc", campaign_id=sibling["id"],
                entry=[{"type": "p", "children": [{"text": "Hates winter and guilds."}]}])

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        search = loaded_ability(registry, "rpg_core", "lore_search")
        assert search is not None
        got = search(registry, str(person.id), campaign["id"], "Old Tam frets about the guild and winter")
        records = [passage["record_id"] for passage in got["passages"]]
        # Tam is named, so his first passage leads; then the passages sharing the text's words; never
        # the sibling campaign's or the other setting's.
        assert records[0] == tam["id"] and got["passages"][0]["path"] == ["Old Tam"] and "exact" in got["passages"][0]["ranks"]
        assert set(records) == {tam["id"], guild["id"], canon["id"]}
        motive = next(passage for passage in got["passages"] if passage["path"] == ["Old Tam", "Motive"])
        assert motive["text"] == "Pay the Guild before winter comes." and motive["tokens"] == 9
        assert got["methods"]["exact"] == "used" and got["methods"]["text"].startswith("basic")
        assert got["methods"]["vector"].startswith("unavailable") and got["methods"]["trigram"].startswith("unavailable")
        # The setting's canon only when asked; record types narrow it; the budget holds.
        assert canon["id"] not in {p["record_id"] for p in search(registry, str(person.id), campaign["id"], "winter", include_setting=False)["passages"]}
        assert {p["record_id"] for p in search(registry, str(person.id), campaign["id"], "winter guild", kinds=["faction"])["passages"]} == {guild["id"]}
        assert sum(p["tokens"] for p in search(registry, str(person.id), campaign["id"], "winter guild Tam", token_budget=12)["passages"]) <= 12
        # Another user reads nothing of this campaign.
        refused = server.post(f"/v1/campaign/{campaign['id']}/lore_search", json={"lore_search": {"text": "winter"}}, headers=_headers(other))
        assert refused.status_code in (403, 404), refused.text

        # A changed entry is cut again; a deleted record's passages go.
        _put(server, person, "person", tam, entry=[{"type": "p", "children": [{"text": "Sold the inn and sailed south."}]}])
        texts = [p["text"] for p in search(registry, str(person.id), campaign["id"], "Old Tam sailed")["passages"] if p["record_id"] == tam["id"]]
        assert texts == ["Sold the inn and sailed south."]
        current = server.get(f"/v1/faction/{guild['id']}", headers=_headers(person))
        gone = server.delete(f"/v1/faction/{guild['id']}", headers=_headers(person, **{"If-Match": current.headers["ETag"]}))
        assert gone.status_code in (200, 204), gone.text
        assert guild["id"] not in {p["record_id"] for p in search(registry, str(person.id), campaign["id"], "winter rates")["passages"]}

        # The REST twin answers the same; the rebuild finds nothing left to index.
        posted = server.post(f"/v1/campaign/{campaign['id']}/lore_search", json={"lore_search": {"text": "Old Tam sailed"}}, headers=_headers(person))
        assert posted.status_code == 200, posted.text
        assert posted.json()["passages"][0]["record_id"] == tam["id"]
        rebuild = loaded_ability(registry, "rpg_core", "rebuild_lore_chunks")
        assert rebuild is not None and set(rebuild(registry, str(person.id)).values()) == {0}

    def test_embedding_waits_for_postgres_and_holds_its_width(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability
        from zephyrex.extensions.rpg_core import LoreSearch  # type: ignore[import-not-found]

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        calls: list[list[str]] = []
        register = loaded_ability(registry, "rpg_core", "register_embedder")
        assert register is not None
        try:
            register(registry, str(person.id), lambda texts: calls.append(texts) or [[0.0] * 768 for _ in texts], "test-embed")
            assert LoreSearch.embedder() is not None and LoreSearch.embedder()[1] == "test-embed"  # type: ignore[index]
            # SQLite has no embedding column: nothing is embedded, and lore_search says why.
            assert LoreSearch.embed_pending(registry) == 0 and calls == []
            campaign = _create(server, person, "campaign", name="Vectorless")
            got = LoreSearch.lore_search(registry, str(person.id), campaign["id"], "anything")
            assert got.methods["vector"].startswith("unavailable: needs Postgres with pgvector")
        finally:
            LoreSearch._registered.clear()
        # A model of the wrong width is refused by name, never stored.
        with pytest.raises(ValueError, match="768"):
            LoreSearch._vector_literal([0.0] * 384)



class TestEmbeddingPace:
    """Self Hosted AI, 2026-11-23: the embed card is shared, so the full backfill runs off-hours,
    one request at a time, backing off on failure; bifrost wants a bearer token."""

    def test_the_backfill_window(self) -> None:
        from zephyrex.extensions.rpg_core.LoreSearch import in_backfill_window  # type: ignore[import-not-found]

        assert [hour for hour in range(24) if in_backfill_window(hour)] == [1, 2, 3, 4, 5, 6]
        assert [hour for hour in range(24) if in_backfill_window(hour, "22-3")] == [0, 1, 2, 22, 23]
        assert all(in_backfill_window(hour, "always") for hour in range(24)) and not any(in_backfill_window(hour, "never") for hour in range(24))

    def test_a_failing_embedder_backs_off_and_never_stops_the_loop(self, server: TestClient) -> None:
        import asyncio

        from zephyrex.extensions.rpg_core import LoreSearch  # type: ignore[import-not-found]

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        service = LoreSearch.LoreEmbeddingService(requester_id="root", model_registry=registry)
        LoreSearch.register_embedder(lambda texts: [[0.0] * 768 for _ in texts], "test")
        original = LoreSearch.embed_pending
        try:
            def failing(*_args: object, **_kwargs: object) -> int:
                raise RuntimeError("502 Bad Gateway")

            LoreSearch.embed_pending = failing
            asyncio.run(service.update())
            assert service._backoff == 30.0 and service._resume_at > 0
            service._resume_at = 0.0
            asyncio.run(service.update())
            assert service._backoff == 60.0
            LoreSearch.embed_pending = lambda *_args, **_kwargs: 0
            service._resume_at = 0.0
            asyncio.run(service.update())
            assert service._backoff == 0.0
        finally:
            LoreSearch.embed_pending = original
            LoreSearch._registered.clear()

    def test_the_http_embedder_sends_a_bearer_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import io
        import json as jsonlib

        from zephyrex.extensions.rpg_core import LoreSearch  # type: ignore[import-not-found]

        seen: dict[str, object] = {}

        class Answer(io.BytesIO):
            def __enter__(self) -> "Answer":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

        def opened(request: object, timeout: float) -> Answer:
            seen["auth"] = request.get_header("Authorization")  # type: ignore[attr-defined]
            seen["body"] = jsonlib.loads(request.data)  # type: ignore[attr-defined]
            return Answer(jsonlib.dumps({"data": [{"index": 0, "embedding": [0.5]}]}).encode())

        monkeypatch.setattr(LoreSearch.urllib.request, "urlopen", opened)
        monkeypatch.delenv("WIKI_EMBED_KEY", raising=False)
        assert LoreSearch._http_embedder("http://embed.invalid/v1", "3-5gb/nomic-embed-text-v1.5")(["search_query: hi"]) == [[0.5]]
        assert seen == {"auth": "Bearer wiki", "body": {"model": "3-5gb/nomic-embed-text-v1.5", "input": ["search_query: hi"]}}



class TestTtsVoice:
    """Operator, 2026-11-23: "A voice per character (picked on the character, the narrator its own)"."""

    def test_set_served_cleared_filled_and_copied(self, server: TestClient, person: Any) -> None:
        scenario = _create(server, person, "campaign", name="Voiced Scenario", is_scenario=True)
        tam = _create(server, person, "person", name="Voiced Tam", kind="npc", campaign_id=scenario["id"], tts_voice="  onyx ")
        assert tam["tts_voice"] == "onyx"
        row = lambda one: server.get(f"/v1/world_entity?ids={one}", headers=_headers(person)).json()["world_entities"][0]  # noqa: E731
        assert row(tam["id"])["tts_voice"] == "onyx"
        # A person's own kind rides along (Zephyrex RPG: a PC told from an NPC without its tags).
        assert row(tam["id"])["person_kind"] == "npc"
        hero = _create(server, person, "person", name="Kind Hero", kind="pc", campaign_id=scenario["id"])
        assert row(hero["id"])["person_kind"] == "pc"
        listed = {one["name"]: one for one in server.get(f"/v1/world_entity?campaign_id={scenario['id']}", headers=_headers(person)).json()["world_entities"]}
        assert (listed["Kind Hero"]["person_kind"], listed["Voiced Tam"]["person_kind"]) == ("pc", "npc")
        # The picker: the person's own route; "" is back to the default; too long is refused.
        assert _put(server, person, "person", tam, tts_voice="alloy").status_code == 200
        assert row(tam["id"])["tts_voice"] == "alloy"
        assert _put(server, person, "person", tam, tts_voice="v" * 65).status_code == 422
        assert _put(server, person, "person", tam, tts_voice="").status_code == 200
        assert row(tam["id"])["tts_voice"] is None
        # An agent's fill_person sets it too.
        filled = server.post(f"/v1/campaign/{scenario['id']}/fill_person", json={"person": {"person_id": tam["id"], "tts_voice": "echo"}}, headers=_headers(person))
        assert filled.status_code == 200, filled.text
        assert filled.json()["person"]["updated"] == ["tts_voice"] and row(tam["id"])["tts_voice"] == "echo"
        # Copied at start.
        _run, ids = _started(server, person, _start_with(server, person, scenario["id"], []))
        assert row(ids[tam["id"]])["tts_voice"] == "echo"


class TestEras:
    """Operator, 2026-11-23: Reality's eras work like the 40k lines: a campaign sees its era's canon
    and every era-less canon record of its setting, never another era's."""

    def test_a_campaign_sees_its_eras_canon_and_the_era_less(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        reality = _create(server, person, "setting", name="Era Reality")
        victorian = _create(server, person, "taxon", name="Victorian", kind="era", setting_id=reality["id"])
        cold_war = _create(server, person, "taxon", name="Cold War", kind="era", setting_id=reality["id"])
        london = _create(server, person, "location", name="London", kind="city", setting_id=reality["id"])
        gaslight = _create(server, person, "item", name="Gaslight Lamp", kind="misc", setting_id=reality["id"])
        bunker = _create(server, person, "location", name="Fallout Bunker", kind="facility", setting_id=reality["id"])
        for taxon, record, kind in ((victorian, gaslight, "item"), (cold_war, bunker, "location")):
            _create(server, person, "entity_taxon", taxon_id=taxon["id"], target_entity_type=kind, target_entity_id=record["id"])
        scenario = _create(server, person, "campaign", name="Ripper Hunt", setting_id=reality["id"], is_scenario=True)
        _create(server, person, "entity_taxon", taxon_id=victorian["id"], target_entity_type="campaign", target_entity_id=scenario["id"])
        eraless = _create(server, person, "campaign", name="Anywhen", setting_id=reality["id"])

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        synced = lambda campaign: {e["name"] for e in server.get(f"/v1/world_entity?campaign_id={campaign}&include_setting=true", headers=_headers(person)).json()["world_entities"]}  # noqa: E731
        assert synced(scenario["id"]) == {"London", "Gaslight Lamp"}
        assert synced(eraless["id"]) == {"London", "Gaslight Lamp", "Fallout Bunker"}
        matching = loaded_ability(registry, "rpg_core", "world_entities_matching")
        named = {e["name"] for e in matching(registry, str(person.id), scenario["id"], "From London the gaslight lamp leads to the fallout bunker")["world_entities"]}
        assert named == {"London", "Gaslight Lamp"}
        search = loaded_ability(registry, "rpg_core", "lore_search")
        found = {p["name"] for p in search(registry, str(person.id), scenario["id"], "London gaslight lamp fallout bunker")["passages"]}
        assert "Fallout Bunker" not in found and "London" in found
        # A playthrough keeps its scenario's era.
        _run, ids = _started(server, person, _start_with(server, person, scenario["id"], []))
        assert synced(ids[scenario["id"]]) == {"London", "Gaslight Lamp"}


class TestCardPerson:
    """Parity, 2026-11-23: chatting with a SillyTavern card needs a wiki person (rpg-ai's cast is
    wiki persons); the operator: "a character card imports as a wiki person with its voice"."""

    CARD = {
        "name": "Vel",
        "description": "A courier with a debt.",
        "personality": "Wry.",
        "scenario": "A rain-soaked dock.",
        "first_message": "Late again, {{user}}?",
        "example_messages": "<START>{{char}}: Hm.",
        "alternate_greetings": ["Back so soon?"],
        "tags": ["Courier"],
        "avatar": "https://example.invalid/vel.png",
    }

    def test_a_card_becomes_a_person_of_the_requesters_characters_campaign(self, server: TestClient, person: Any, other: Any) -> None:
        made = server.post("/v1/campaign/card_person", json={"card": self.CARD}, headers=_headers(person))
        assert made.status_code == 201, made.text
        ids = made.json()
        vel = server.get(f"/v1/person/{ids['person_id']}", headers=_headers(person)).json()["person"]
        assert (vel["name"], vel["kind"], vel["campaign_id"], vel["picture_url"]) == ("Vel", "npc", ids["campaign_id"], "https://example.invalid/vel.png")
        assert json.loads(vel["voice"])["first_message"] == "Late again, User?" and json.loads(vel["voice"])["examples"] == ["Vel: Hm."]
        campaign = server.get(f"/v1/campaign/{ids['campaign_id']}", headers=_headers(person)).json()["campaign"]
        assert campaign["name"] == "Characters" and not campaign.get("is_scenario")
        row = server.get(f"/v1/world_entity?ids={ids['person_id']}", headers=_headers(person)).json()["world_entities"][0]
        assert row["tags"] == ["Courier"] and row["gm_only"] is False and "rain-soaked dock" in row["summary"] + json.dumps(vel["entry"])
        greetings = [p for p in server.get(f"/v1/record_metadata/of?target_entity_type=person&target_entity_id={ids['person_id']}", headers=_headers(person)).json()["metadata"] if p["key"] == "Alternate greetings"]
        assert greetings[0]["value"] == "Back so soon?" and greetings[0]["is_private"] is True
        # A second card of the same name is a second person, in the same campaign.
        again = server.post("/v1/campaign/card_person", json={"card": self.CARD}, headers=_headers(person)).json()
        assert again["campaign_id"] == ids["campaign_id"] and again["person_id"] != ids["person_id"]
        # Another user's card goes into their own Characters campaign.
        theirs = server.post("/v1/campaign/card_person", json={"card": {"name": "Holst"}}, headers=_headers(other)).json()
        assert theirs["campaign_id"] != ids["campaign_id"]
        # A data URL is uploaded first.
        refused = server.post("/v1/campaign/card_person", json={"card": {"name": "Pic", "avatar": "data:image/png;base64,AAAA"}}, headers=_headers(person))
        assert refused.status_code == 422, refused.text


class TestKnownFacts:
    """Operator, 2026-11-24: a player's view shows what their character has learned. A known fact
    is the campaign's GM's to write; learn_fact makes the same fact once."""

    def test_written_by_the_gm_once_each_and_gone_with_the_campaign(self, server: TestClient, person: Any, other: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        campaign = _create(server, person, "campaign", name="Known Facts")
        hero = _create(server, person, "person", name="Ilsa", kind="pc", campaign_id=campaign["id"])
        keep = _create(server, person, "location", name="The Keep", campaign_id=campaign["id"])
        made = server.post(
            "/v1/known_fact",
            json={"known_fact": {"person_id": hero["id"], "target_entity_type": "location", "target_entity_id": keep["id"], "text": "  The gate sticks.  "}},
            headers=_headers(person),
        )
        assert made.status_code in (200, 201), made.text
        fact = made.json()["known_fact"]
        assert (fact["text"], fact["campaign_id"]) == ("The gate sticks.", campaign["id"])
        # A type that isn't a record's, and too much text: refused.
        for bad in ({"target_entity_type": "dragon"}, {"text": "x" * 2001}):
            body = {"person_id": hero["id"], "target_entity_type": "location", "target_entity_id": keep["id"], **bad}
            assert server.post("/v1/known_fact", json={"known_fact": body}, headers=_headers(person)).status_code == 422
        # Someone who isn't the campaign's GM can't say what its people know.
        theirs = {"person_id": hero["id"], "target_entity_type": "location", "target_entity_id": keep["id"]}
        assert server.post("/v1/known_fact", json={"known_fact": theirs}, headers=_headers(other)).status_code in (403, 404)

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        learn = loaded_ability(registry, "rpg_core", "learn_fact")
        assert learn is not None
        knows_of = learn(registry, str(person.id), hero["id"], "location", keep["id"])
        assert (knows_of["created"], knows_of["known_fact"]["text"]) == (True, None)
        again = learn(registry, str(person.id), hero["id"], "location", keep["id"], "The gate sticks.")
        assert (again["created"], again["known_fact"]["id"]) == (False, fact["id"])
        listed = server.get("/v1/known_fact", params={"person_id": hero["id"], "target_entity_id": keep["id"]}, headers=_headers(person)).json()
        assert sorted(str(one["text"]) for one in listed["known_facts"]) == ["None", "The gate sticks."]

        # Deleting the campaign takes its facts with it.
        assert server.delete(f"/v1/campaign/{campaign['id']}", headers=_headers(person, **{"If-Match": f'"{campaign["updated_at"] or campaign["created_at"]}"'})).status_code in (200, 204)
        left = server.get("/v1/known_fact", params={"campaign_id": campaign["id"]}, headers=_headers(person)).json()
        assert left["known_facts"] == []


class TestCurrentAttitudes:
    """Operator, 2026-11-24: "Combat sides should be based on character disposition". The current
    attitude between each pair of a campaign's people, and toward the party, as its band; none or
    "missing" is absent."""

    def test_by_resolved_trigger_else_the_default_as_a_band(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        campaign = _create(server, person, "campaign", name="Sides")
        a, b, c = (_create(server, person, "person", name=name, kind="npc", campaign_id=campaign["id"]) for name in ("Ada", "Bram", "Cass"))
        betrayal = _create(server, person, "hook", name="The betrayal", campaign_id=campaign["id"])
        toward = lambda who, target, attitude, **more: _create(  # noqa: E731
            server, person, "disposition", person_id=who["id"], target_kind="person", target_person_id=target["id"], attitude=attitude, **more
        )
        toward(a, b, "warm", is_default=True)  # a nuance: read as its band, helpful
        toward(a, b, "hostile", trigger_hook_id=betrayal["id"])  # not yet resolved
        toward(b, a, "wary", is_default=True)
        toward(c, a, "missing", is_default=True)  # absent
        _create(server, person, "disposition", person_id=c["id"], target_kind="party", attitude="enraged", is_default=True)  # toward the party
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        read = loaded_ability(registry, "rpg_core", "current_attitudes")
        assert read is not None
        ids = [a["id"], b["id"], c["id"]]
        assert read(registry, str(person.id), campaign["id"], ids) == {a["id"]: {b["id"]: "helpful"}, b["id"]: {a["id"]: "wary"}, c["id"]: {"party": "enraged"}}
        # The betrayal happens: Ada's trigger entry is current.
        _put(server, person, "hook", betrayal, resolved_at="2026-11-24T01:00:00")
        assert read(registry, str(person.id), campaign["id"], ids)[a["id"]] == {b["id"]: "hostile"}
        # One person: only their attitude toward the party; none in the campaign: nothing.
        assert read(registry, str(person.id), campaign["id"], [c["id"]]) == {c["id"]: {"party": "enraged"}}
        assert read(registry, str(person.id), campaign["id"], [a["id"]]) == {}
        assert read(registry, str(person.id), campaign["id"], ["not-a-person"]) == {}


class TestInstantiateHooks:
    """Parity, 2026-11-24 (the operator's Foundry option: rpg-ai reaches nothing internal): a
    composing app registers its after-start hook through an ability, once."""

    def test_registered_once_called_after_a_start_and_a_failure_never_undoes_it(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability
        from zephyrex.extensions.rpg_core.BLL_RPGCore import AFTER_INSTANTIATE  # type: ignore[import-not-found]

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        register = loaded_ability(registry, "rpg_core", "register_instantiate_hook")
        assert register is not None
        seen: list[tuple[str, str, int]] = []

        def copy_frame(model_registry: Any, requester_id: str, source: str, made: str, id_map: dict[str, str]) -> None:
            seen.append((source, made, len(id_map)))

        def broken(model_registry: Any, requester_id: str, source: str, made: str, id_map: dict[str, str]) -> None:
            raise RuntimeError("this hook fails")

        held = list(AFTER_INSTANTIATE)
        try:
            assert register(registry, str(person.id), copy_frame) == {"registered": True}
            assert register(registry, str(person.id), copy_frame) == {"registered": False}
            assert register(registry, str(person.id), broken) == {"registered": True}
            scenario = _create(server, person, "campaign", name="Hooked Scenario", is_scenario=True)
            _create(server, person, "person", name="Hooked NPC", kind="npc", campaign_id=scenario["id"])
            start = _start(server, person, scenario["id"], "Hooked Run")
            # The broken hook is logged; the start still ends done, and the other hook ran once.
            assert start["state"] == "done", start
            assert len(seen) == 1 and seen[0][0] == scenario["id"] and seen[0][1] == start["campaign_id"] and seen[0][2] >= 1
        finally:
            AFTER_INSTANTIATE[:] = held


class TestCampaignBackends:
    """The operator, 2026-11-24 ("Framework selector"): a campaign kept in a Foundry world. Its
    backend is native unless set; rpg_core's selector names the backend of a call's campaign, found
    from its campaign_id or a person or record it names."""

    def test_the_selector_reads_the_calls_campaign(self, server: TestClient, person: Any, other: Any) -> None:
        from zephyrex.extensions.rpg_core.EXT_RPGCore import RPGCoreExtension  # type: ignore[import-not-found]

        native = _create(server, person, "campaign", name="Kept Here")
        foundry = _create(server, person, "campaign", name="Kept in Foundry", backend="foundry")
        assert (native.get("backend"), foundry["backend"]) == (None, "foundry")
        refused = server.post("/v1/campaign", json={"campaign": {"name": "Elsewhere", "backend": "roll20"}}, headers=_headers(person))
        assert refused.status_code == 422, refused.text
        hero = _create(server, person, "person", name="Foundry Hero", kind="pc", campaign_id=foundry["id"])
        inn = _create(server, person, "location", name="Foundry Inn", campaign_id=foundry["id"])
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        call = {"model_registry": registry, "requester_id": str(person.id)}
        select = RPGCoreExtension.select_backend
        assert select("world_entities", {**call, "campaign_id": native["id"]}) is None
        assert select("world_entities", {**call, "campaign_id": foundry["id"]}) == "foundry"
        assert select("move_person", {**call, "person_id": hero["id"], "location_id": inn["id"]}) == "foundry"
        assert select("world_entities_by_id", {**call, "ids": [inn["id"]]}) == "foundry"
        # A Foundry id ("fvtt:<world>:<uuid>") is Foundry's, with nothing looked up.
        assert select("move_person", {**call, "person_id": "fvtt:w1:Actor.abc", "location_id": "fvtt:w1:Scene.def"}) == "foundry"
        assert select("world_entities_by_id", {**call, "ids": ["fvtt:w1:Actor.abc"]}) == "foundry"
        assert select("current_attitudes", {**call, "campaign_id": foundry["id"], "person_ids": [hero["id"]]}) == "foundry"
        # Nothing that names a campaign, or no registry: native. (Read as ROOT: the ability itself
        # holds the caller to its access, after the selector picked its backend.)
        assert select("register_embedder", {**call, "model": "x"}) is None
        assert select("world_entities", {"campaign_id": foundry["id"]}) is None
        # The ability VTT's selectors read: a campaign's, or a person's campaign's; unknown is native.
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        read = loaded_ability(registry, "rpg_core", "campaign_backend")
        assert read is not None
        assert read(registry, str(person.id), campaign_id=foundry["id"]) == {"backend": "foundry", "world_id": None, "campaign_id": foundry["id"], "member": True}
        # Another user: the same routing answer, but not a member (external_vtt reads nothing for them).
        assert read(registry, str(other.id), campaign_id=foundry["id"]) == {"backend": "foundry", "world_id": None, "campaign_id": foundry["id"], "member": False}
        assert read(registry, str(other.id), person_id=hero["id"])["backend"] == "foundry"
        assert read(registry, str(person.id), campaign_id="no-such-campaign") == {"backend": "native", "world_id": None, "campaign_id": None, "member": False}
        assert read(registry, str(person.id)) == {"backend": "native", "world_id": None, "campaign_id": None, "member": False}
        # By world (external_vtt's id-only reads): the requester's Foundry campaign on it; a
        # non-member, or a world no campaign is kept in, finds none.
        world = _foundry_world(server)
        assert server.post("/v1/campaign", json={"campaign": {"name": "Nowhere", "backend": "foundry", "foundry_world_id": "no-such-world"}}, headers=_headers(person)).status_code == 422
        on_world = _create(server, person, "campaign", name="On a World", backend="foundry", foundry_world_id=world)
        assert read(registry, str(person.id), world_id=world) == {"backend": "foundry", "world_id": world, "campaign_id": on_world["id"], "member": True}
        assert read(registry, str(other.id), world_id=world)["campaign_id"] is None
        assert read(registry, str(person.id), world_id="no-such-world")["campaign_id"] is None
        # Back to native: none or "native" both read as the wiki's own.
        moved = _put(server, person, "campaign", foundry, backend="native")
        assert moved.status_code == 200, moved.text
        assert select("world_entities", {**call, "campaign_id": foundry["id"]}) is None


def _foundry_world(server: TestClient) -> str:
    """A provider instance standing in for a Foundry world (a campaign's foundry_world_id)."""
    import uuid

    from zephyrex.lib.Environment import env
    from zephyrex.logic.BLL_Providers import ProviderInstanceManager, ProviderManager

    registry = server.app.state.model_registry  # type: ignore[attr-defined]
    root = env("ROOT_ID")
    provider = ProviderManager(model_registry=registry, requester_id=root).create(name=f"foundry_{uuid.uuid4().hex}")
    return str(ProviderInstanceManager(model_registry=registry, requester_id=root).create(name=f"world_{uuid.uuid4().hex}", provider_id=provider.id).id)


class TestPlaythroughIsNoScenario:
    """Zephyrex RPG, 2026-11-24: the operator's Missing Merchant playthrough was marked a scenario. A
    start makes a playthrough that isn't one, and nothing may mark one a scenario after."""

    def test_a_start_is_no_scenario_and_cannot_be_made_one(self, server: TestClient, person: Any) -> None:
        scenario = _create(server, person, "campaign", name="Flagged Scenario", is_scenario=True)
        _create(server, person, "person", name="Flagged NPC", kind="npc", campaign_id=scenario["id"])
        start = _start(server, person, scenario["id"])
        assert start["state"] == "done", start
        run = server.get(f"/v1/campaign/{start['campaign_id']}", headers=_headers(person)).json()["campaign"]
        assert (run["is_scenario"], run["scenario_id"]) == (False, scenario["id"])
        refused = _put(server, person, "campaign", run, is_scenario=True)
        assert refused.status_code == 422, refused.text
        made = server.post("/v1/campaign", json={"campaign": {"name": "Odd", "is_scenario": True, "scenario_id": scenario["id"]}}, headers=_headers(person))
        assert made.status_code == 422, made.text
        # A scenario stays one.
        assert _put(server, person, "campaign", scenario, description="Still a scenario.").status_code == 200
        # Nor can an update give a scenario a scenario_id (Zephyrex RPG, 2026-11-24: "can't happen during
        # updates ever"): Update has no scenario_id, so a campaign's is fixed at its create.
        other = _create(server, person, "campaign", name="Other Scenario", is_scenario=True)
        _put(server, person, "campaign", other, scenario_id=scenario["id"])
        held = server.get(f"/v1/campaign/{other['id']}", headers=_headers(person)).json()["campaign"]
        assert (held["is_scenario"], held["scenario_id"]) == (True, None)


class TestUnnamedAndKnownNames:
    """Operator, 2026-11-25: "NPCs should have generic descriptions unless the player knows their name
    which gets replaced as names are learned." A person's unnamed_as (their own, else a generic one),
    and whose names the party knows."""

    def test_a_person_reads_by_a_description_until_the_party_knows_their_name(self, server: TestClient, person: Any, other: Any) -> None:
        world = _create(server, person, "campaign", name="Saltmere Run")
        tam = _create(server, person, "person", name="Tam", kind="pc", campaign_id=world["id"])
        wren = _create(server, person, "person", name="Wren", kind="pc", campaign_id=world["id"])
        mags = _create(server, person, "person", name="Mags Thornbury", kind="npc", campaign_id=world["id"], unnamed_as="  a woman in a grey hood ")
        brom = _create(server, person, "person", name="Brom", kind="npc", campaign_id=world["id"], gender="female")
        nobody = _create(server, person, "person", name="Quill", kind="npc", campaign_id=world["id"])
        dwarf = _create(server, person, "taxon", name="Dwarf", kind="race", campaign_id=world["id"])
        _create(server, person, "entity_taxon", taxon_id=dwarf["id"], target_entity_type="person", target_entity_id=brom["id"])
        assert mags["unnamed_as"] == "a woman in a grey hood"
        too_long = server.post("/v1/person", json={"person": {"name": "Long", "campaign_id": world["id"], "unnamed_as": "x" * 121}}, headers=_headers(person))
        assert too_long.status_code == 422, too_long.text

        seen = {one["name"]: one for one in server.get(f"/v1/world_entity?campaign_id={world['id']}", headers=_headers(person)).json()["world_entities"]}
        assert (seen["Mags Thornbury"]["unnamed_as"], seen["Brom"]["unnamed_as"], seen["Quill"]["unnamed_as"]) == ("a woman in a grey hood", "a dwarf woman", "a stranger")
        by_id = server.get(f"/v1/world_entity?ids={mags['id']},{brom['id']}", headers=_headers(person)).json()["world_entities"]
        assert [one["unnamed_as"] for one in by_id] == ["a woman in a grey hood", "a dwarf woman"]
        # Cleared, a person reads by the generic one again.
        assert _put(server, person, "person", mags, unnamed_as="").status_code == 200
        again = {one["name"]: one for one in server.get(f"/v1/world_entity?campaign_id={world['id']}", headers=_headers(person)).json()["world_entities"]}
        assert again["Mags Thornbury"]["unnamed_as"] == "a stranger"

        # Their gender as authored, for pronouns (operator, 2026-11-25: "It's misgendering characters
        # … Need pronoun enforcement"): the field, else a public Gender property (vault_import's
        # gender:), never a private one.
        seraphine = _create(server, person, "person", name="Seraphine Dusk", kind="npc", campaign_id=world["id"])
        hidden = _create(server, person, "person", name="Veiled", kind="npc", campaign_id=world["id"])
        for who, private in ((seraphine, False), (hidden, True)):
            said = server.post(
                "/v1/record_metadata",
                json={"record_metadata": {"target_entity_type": "person", "target_entity_id": who["id"], "key": "Gender", "value": "female", "value_type": "text", "is_private": private}},
                headers=_headers(person),
            )
            assert said.status_code in (200, 201), said.text
        gendered = {one["name"]: one for one in server.get(f"/v1/world_entity?campaign_id={world['id']}", headers=_headers(person)).json()["world_entities"]}
        assert (gendered["Brom"]["gender"], gendered["Seraphine Dusk"]["gender"], gendered["Veiled"]["gender"], gendered["Quill"]["gender"]) == ("female", "female", None, None)
        assert gendered["Seraphine Dusk"]["unnamed_as"] == "a woman"
        matched = server.post(f"/v1/campaign/{world['id']}/matching", json={"matching": {"text": "Seraphine Dusk walks in."}}, headers=_headers(person)).json()["world_entities"]
        assert [one["gender"] for one in matched if one["name"] == "Seraphine Dusk"] == ["female"]

        # Knowing of a person is knowing their name; a fact about them alone is not.
        for body in (
            {"person_id": tam["id"], "target_entity_type": "person", "target_entity_id": mags["id"]},
            {"person_id": wren["id"], "target_entity_type": "person", "target_entity_id": brom["id"], "text": "The dwarf at the bar pours short."},
        ):
            made = server.post("/v1/known_fact", json={"known_fact": body}, headers=_headers(person))
            assert made.status_code == 201, made.text
        known = server.get(f"/v1/campaign/{world['id']}/known_names", headers=_headers(person))
        assert known.status_code == 200, known.text
        names = known.json()["known_names"]
        assert names["party"] == sorted([tam["id"], wren["id"], mags["id"]])
        assert names["by_pc"] == {tam["id"]: sorted([tam["id"], wren["id"], mags["id"]]), wren["id"]: sorted([tam["id"], wren["id"]])}
        assert nobody["id"] not in names["party"] and brom["id"] not in names["party"]
        # For rpg-ai in process, the same.
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        assert loaded_ability(registry, "rpg_core", "known_names")(registry, str(person.id), world["id"]) == names
        # Someone who can't see the campaign learns nothing of it.
        assert server.get(f"/v1/campaign/{world['id']}/known_names", headers=_headers(other)).status_code in (403, 404)
        empty = _create(server, person, "campaign", name="No Party")
        assert server.get(f"/v1/campaign/{empty['id']}/known_names", headers=_headers(person)).json()["known_names"] == {"party": [], "by_pc": {}}

    def test_a_scenario_says_whom_the_party_knows_from_the_start(self, server: TestClient, person: Any) -> None:
        """Operator, 2026-11-25, of a scenario's patron: "Presumably he hired them so they should know
        his name. This is campaign context that should be in the scenario." known_to_party is known
        to every PC: copied on start, and read through the scenario by name for an older copy."""
        scenario = _create(server, person, "campaign", name="Haunted Manor Test", is_scenario=True)
        _create(server, person, "person", name="Bastian", kind="npc", campaign_id=scenario["id"], known_to_party=True)
        _create(server, person, "person", name="Hester", kind="npc", campaign_id=scenario["id"])
        _create(server, person, "person", name="Seraph", kind="pc", campaign_id=scenario["id"])
        start = _start(server, person, scenario["id"])
        assert start["state"] == "done", start
        run = start["campaign_id"]
        people = {one["name"]: one for one in _rows(server.get(f"/v1/person?campaign_id={run}", headers=_headers(person)).json())}
        assert people["Bastian"]["known_to_party"] is True
        names = server.get(f"/v1/campaign/{run}/known_names", headers=_headers(person)).json()["known_names"]
        assert people["Bastian"]["id"] in names["party"] and people["Hester"]["id"] not in names["party"]
        assert names["by_pc"][people["Seraph"]["id"]] == sorted([people["Seraph"]["id"], people["Bastian"]["id"]])
        # A playthrough copied before the mark (no known_to_party on its copy) reads it from its scenario.
        older = _create(server, person, "campaign", name="Older Run", scenario_id=scenario["id"])
        copy = _create(server, person, "person", name="Bastian", kind="npc", campaign_id=older["id"])
        pc = _create(server, person, "person", name="Seraph", kind="pc", campaign_id=older["id"])
        assert server.get(f"/v1/campaign/{older['id']}/known_names", headers=_headers(person)).json()["known_names"]["party"] == sorted([copy["id"], pc["id"]])


class TestInvariants:
    """Operator, 2026-11-28: NPCs get character invariants, lines they never cross ("never harms a
    child", "never breaks a sworn oath"). A list of short sentences on the person: edited as their
    other fields, copied on start, and in the world-entity reads rpg-ai holds their turns to."""

    def test_a_persons_invariants_are_kept_copied_and_read(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        scenario = _create(server, person, "campaign", name="Oathbound Test", is_scenario=True)
        oaths = [" Never harms a child ", "Never breaks a sworn oath", "Never harms a child", ""]
        warden = _create(server, person, "person", name="Warden", kind="npc", campaign_id=scenario["id"], invariants=oaths)
        assert json.loads(warden["invariants"]) == ["Never harms a child", "Never breaks a sworn oath"]
        plain = _create(server, person, "person", name="Plain", kind="npc", campaign_id=scenario["id"])
        assert plain["invariants"] is None
        # Edited as their other fields.
        changed = _put(server, person, "person", warden, invariants=["Never harms a child", "Never lies to a priest"])
        assert changed.status_code == 200, changed.text
        for bad in ("not a list", [f"x{index}" for index in range(13)], ["x" * 201]):
            assert _put(server, person, "person", warden, invariants=bad).status_code == 422, bad
        # Read where rpg-ai reads the world: the sync and by id.
        synced = {one["name"]: one for one in server.get(f"/v1/world_entity?campaign_id={scenario['id']}", headers=_headers(person)).json()["world_entities"]}
        assert (synced["Warden"]["invariants"], synced["Plain"]["invariants"]) == (["Never harms a child", "Never lies to a priest"], [])
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        [by_id] = loaded_ability(registry, "rpg_core", "world_entities_by_id")(registry, str(person.id), [warden["id"]])["world_entities"]
        assert by_id["invariants"] == ["Never harms a child", "Never lies to a priest"]
        # A start copies them with the person.
        start = _start(server, person, scenario["id"])
        assert start["state"] == "done", start
        copies = {one["name"]: one for one in _rows(server.get(f"/v1/person?campaign_id={start['campaign_id']}", headers=_headers(person)).json())}
        assert json.loads(copies["Warden"]["invariants"]) == ["Never harms a child", "Never lies to a priest"]


class TestSetAttitude:
    """Zephyrex RPG, 2026-11-28: play writes an attitude back for the story's dispositions check;
    current_attitudes reads it at once, and a trigger resolved later still wins."""

    def test_the_entry_in_effect_changes_else_a_default_is_made(self, server: TestClient, person: Any, other: Any) -> None:
        from fastapi import HTTPException
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        campaign = _create(server, person, "campaign", name="Grudges")
        ada, bram = (_create(server, person, "person", name=name, kind="npc", campaign_id=campaign["id"]) for name in ("Ada", "Bram"))
        guild = _create(server, person, "faction", name="The Guild", campaign_id=campaign["id"])
        feud = _create(server, person, "hook", name="The feud", campaign_id=campaign["id"])
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        write = loaded_ability(registry, "rpg_core", "set_attitude")
        read = loaded_ability(registry, "rpg_core", "current_attitudes")
        assert write is not None and read is not None
        ids = [ada["id"], bram["id"]]
        # None toward the party yet: a default is made.
        first = write(registry, str(person.id), ada["id"], "party", "wary", "Caught them in the vault")
        assert (first["created"], first["toward"], first["attitude"]) == (True, "party", "wary")
        assert read(registry, str(person.id), campaign["id"], ids)[ada["id"]] == {"party": "wary"}
        # Again: the same default changes.
        again = write(registry, str(person.id), ada["id"], "party", "hostile")
        assert (again["created"], again["disposition_id"]) == (False, first["disposition_id"])
        # Toward a person with an authored default and a trigger: the default until the trigger resolves.
        _create(server, person, "disposition", person_id=ada["id"], target_kind="person", target_person_id=bram["id"], attitude="friendly", is_default=True)
        triggered = _create(server, person, "disposition", person_id=ada["id"], target_kind="person", target_person_id=bram["id"], attitude="hostile", trigger_hook_id=feud["id"])
        assert write(registry, str(person.id), ada["id"], bram["id"], "cautious-neutral")["created"] is False
        assert read(registry, str(person.id), campaign["id"], ids)[ada["id"]] == {"party": "hostile", bram["id"]: "cautious-neutral"}
        _put(server, person, "hook", feud, resolved_at="2026-11-28T01:00:00")
        assert read(registry, str(person.id), campaign["id"], ids)[ada["id"]][bram["id"]] == "hostile"
        # Once the trigger is in effect, the write changes that entry.
        assert write(registry, str(person.id), ada["id"], bram["id"], "neutral")["disposition_id"] == triggered["id"]
        assert read(registry, str(person.id), campaign["id"], ids)[ada["id"]][bram["id"]] == "neutral"
        # An organisation; refusals.
        assert write(registry, str(person.id), bram["id"], guild["id"], "helpful")["created"] is True
        # Not on the scale; toward themselves; toward nobody.
        for bad in (("party", "furious"), (ada["id"], "wary"), ("", "wary")):
            try:
                write(registry, str(person.id), ada["id"], *bad)
            except HTTPException as error:
                assert error.status_code == 422, bad
            else:
                raise AssertionError(bad)
        # Someone who can't see the person changes nothing.
        try:
            write(registry, str(other.id), ada["id"], "party", "friendly")
        except HTTPException as error:
            assert error.status_code in (403, 404)
        else:
            raise AssertionError("another account wrote an attitude")


class TestItemsInPlay:
    """Zephyrex RPG, 2026-11-28 (split with Zephyrex VTT): what lies at a place, take, spend and
    drop; carrying is EntityInventory, the owner never changes, a partial move splits a stack and a
    stackable item merges."""

    def test_take_spend_and_drop(self, server: TestClient, person: Any) -> None:
        from fastapi import HTTPException
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        campaign = _create(server, person, "campaign", name="Loot")
        hall = _create(server, person, "location", name="Hall", kind="building", campaign_id=campaign["id"])
        cellar = _create(server, person, "location", name="Cellar", kind="room", campaign_id=campaign["id"], parent_id=hall["id"])
        tam = _create(server, person, "person", name="Tam", kind="pc", campaign_id=campaign["id"], location_id=hall["id"])
        wren = _create(server, person, "person", name="Wren", kind="pc", campaign_id=campaign["id"], location_id=hall["id"])
        potion = _create(server, person, "item", name="Potion of Healing", kind="consumable", stack_size=10)
        sword = _create(server, person, "item", name="Sword", kind="weapon")
        potions = _create(server, person, "item_instance", item_id=potion["id"], location_id=hall["id"], quantity=3)
        blade = _create(server, person, "item_instance", item_id=sword["id"], location_id=cellar["id"], owner_person_id=wren["id"])
        # Wren's gear from before carry rows: owned, held by nothing, lying nowhere.
        kit = _create(server, person, "item_instance", item_id=potion["id"], owner_person_id=wren["id"], quantity=2)
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        call = lambda name, *args: loaded_ability(registry, "rpg_core", name)(registry, str(person.id), *args)  # noqa: E731

        here = call("items_at", hall["id"])["items"]
        assert [(one["name"], one["quantity"]) for one in here] == [("Potion of Healing", 3)]
        assert [one["name"] for one in call("items_at", hall["id"], True)["items"]] == ["Potion of Healing", "Sword"]
        assert [(one["item_instance_id"], one["quantity"]) for one in call("items_carried", [wren["id"]])["items"][wren["id"]]] == [(kit["id"], 2)]

        # Take two of three: the stack splits.
        taken = call("take_item", tam["id"], potions["id"], 2)
        assert (taken["taken"], taken["left"]) == (2, 1) and taken["item_instance_id"] != potions["id"]
        assert [one["quantity"] for one in call("items_at", hall["id"])["items"]] == [1]
        # The last one merges into the stack Tam carries.
        merged = call("take_item", tam["id"], potions["id"])
        assert (merged["item_instance_id"], merged["taken"], merged["left"]) == (taken["item_instance_id"], 1, 0)
        assert call("items_at", hall["id"])["items"] == []
        assert [(one["name"], one["quantity"]) for one in call("items_carried", [tam["id"]])["items"][tam["id"]]] == [("Potion of Healing", 3)]

        # Spend one, then drop the rest in the cellar; then spend one of Wren's legacy kit.
        assert call("spend_item", tam["id"], merged["item_instance_id"])["left"] == 2
        dropped = call("drop_item", tam["id"], merged["item_instance_id"], None, cellar["id"])
        assert (dropped["dropped"], dropped["location_id"]) == (2, cellar["id"])
        assert call("items_carried", [tam["id"]])["items"][tam["id"]] == []
        assert call("spend_item", wren["id"], kit["id"], 2)["left"] == 0
        assert server.get(f"/v1/item_instance/{kit['id']}", headers=_headers(person)).status_code == 404

        # Wren's sword: Tam takes it (the owner stays Wren), and Wren can't take it from him.
        assert call("take_item", tam["id"], blade["id"])["taken"] == 1
        held = server.get(f"/v1/item_instance/{blade['id']}", headers=_headers(person)).json()["item_instance"]
        assert (held["owner_person_id"], held["location_id"]) == (wren["id"], None)
        refusals = [
            ("take_item", wren["id"], blade["id"]),  # Tam carries it
            ("spend_item", wren["id"], blade["id"]),  # Wren doesn't
            ("take_item", tam["id"], dropped["item_instance_id"], 5),  # only 2 there
        ]
        for name, *args in refusals:
            try:
                call(name, *args)
            except HTTPException as error:
                assert error.status_code in (409, 422), (name, error.detail)
            else:
                raise AssertionError((name, args))
        # Dropped where he stands (the hall), by default.
        assert call("drop_item", tam["id"], blade["id"])["location_id"] == hall["id"]

    def test_a_start_copies_the_items_lying_at_its_places(self, server: TestClient, person: Any) -> None:
        scenario = _create(server, person, "campaign", name="Loose Loot Test", is_scenario=True)
        vault = _create(server, person, "location", name="Vault", kind="room", campaign_id=scenario["id"])
        gem = _create(server, person, "item", name="Gem", kind="misc")
        _create(server, person, "item_instance", item_id=gem["id"], location_id=vault["id"], quantity=4)
        _create(server, person, "person", name="Seraph", kind="pc", campaign_id=scenario["id"])
        start = _start(server, person, scenario["id"])
        assert start["state"] == "done", start
        places = _rows(server.get(f"/v1/location?campaign_id={start['campaign_id']}", headers=_headers(person)).json())
        [copy] = [one for one in places if one["name"] == "Vault"]
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        lying = loaded_ability(registry, "rpg_core", "items_at")(registry, str(person.id), copy["id"])["items"]
        assert [(one["name"], one["quantity"]) for one in lying] == [("Gem", 4)]

    def test_as_root_a_spent_item_is_gone(self, server: TestClient, person: Any) -> None:
        """Zephyrex VTT, 2026-11-28: a ROOT read returns soft-deleted rows, and the rows don't carry
        deleted_at, so a spent instance stayed in items_carried; the filter is in the query now."""
        from fastapi import HTTPException
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability
        from zephyrex.lib.Environment import env

        campaign = _create(server, person, "campaign", name="Root Spend")
        hall = _create(server, person, "location", name="Hall", kind="building", campaign_id=campaign["id"])
        tam = _create(server, person, "person", name="Tam", kind="pc", campaign_id=campaign["id"], location_id=hall["id"])
        potion = _create(server, person, "item", name="Potion", kind="consumable", stack_size=10)
        kit = _create(server, person, "item_instance", item_id=potion["id"], owner_person_id=tam["id"], quantity=2)
        loose = _create(server, person, "item_instance", item_id=potion["id"], location_id=hall["id"], quantity=1)
        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        root = str(env("ROOT_ID"))
        call = lambda name, *args: loaded_ability(registry, "rpg_core", name)(registry, root, *args)  # noqa: E731
        assert call("spend_item", tam["id"], kit["id"])["left"] == 1
        assert call("spend_item", tam["id"], kit["id"])["left"] == 0
        assert call("items_carried", [tam["id"]])["items"][tam["id"]] == []
        try:
            call("spend_item", tam["id"], kit["id"])
        except HTTPException as error:
            assert error.status_code == 404
        else:
            raise AssertionError("a spent instance was spent again")
        # A loose one taken and spent is gone from the place and the person, read as ROOT.
        call("take_item", tam["id"], loose["id"])
        call("spend_item", tam["id"], loose["id"])
        assert call("items_at", hall["id"])["items"] == [] and call("items_carried", [tam["id"]])["items"][tam["id"]] == []


class TestRemoveHooks:
    """Zephyrex RPG, 2026-11-28: deleted playthroughs left VTT's person_traits, scene_tokens and
    scenes live on prod. Another extension removes its own rows on a campaign's records through a
    hook the delete calls, with the records' ids, before they go; its counts join the report."""

    def test_called_with_the_records_on_delete_and_dry_run_and_a_failure_never_stops_it(self, server: TestClient, person: Any) -> None:
        from zephyrex.extensions.AbstractExtensionProvider import loaded_ability
        from zephyrex.extensions.rpg_core.BLL_RPGCore import CAMPAIGN_REMOVE_HOOKS, remove_campaign_records  # type: ignore[import-not-found]

        registry = server.app.state.model_registry  # type: ignore[attr-defined]
        register = loaded_ability(registry, "rpg_core", "register_remove_hook")
        assert register is not None
        seen: list[tuple[list[str], set[str], bool]] = []

        def tokens(model_registry: Any, requester_id: str, campaign_ids: list[str], record_ids: list[str], dry_run: bool) -> dict[str, int]:
            seen.append((campaign_ids, set(record_ids), dry_run))
            return {"scenetoken": 2}

        def broken(model_registry: Any, requester_id: str, campaign_ids: list[str], record_ids: list[str], dry_run: bool) -> None:
            raise RuntimeError("this hook fails")

        held = list(CAMPAIGN_REMOVE_HOOKS)
        try:
            assert register(registry, str(person.id), tokens) == {"registered": True}
            assert register(registry, str(person.id), tokens) == {"registered": False}
            assert register(registry, str(person.id), broken) == {"registered": True}
            campaign = _create(server, person, "campaign", name="Doomed Run")
            tam = _create(server, person, "person", name="Tam", kind="pc", campaign_id=campaign["id"])
            inn = _create(server, person, "location", name="Inn", kind="building", campaign_id=campaign["id"])
            # A dry run counts the hook's rows and removes nothing.
            counted = remove_campaign_records(registry, str(person.id), [campaign["id"]], dry_run=True)
            assert counted.removed["scenetoken"] == 2 and seen[-1] == ([campaign["id"]], {tam["id"], inn["id"]}, True)
            assert server.get(f"/v1/person/{tam['id']}", headers=_headers(person)).status_code == 200
            # Deleting the campaign calls it for real; the broken hook is logged and the records go.
            gone = server.delete(f"/v1/campaign/{campaign['id']}", headers=_headers(person, **{"If-Match": f'"{campaign["updated_at"] or campaign["created_at"]}"'}))
            assert gone.status_code in (200, 204), gone.text
            assert seen[-1] == ([campaign["id"]], {tam["id"], inn["id"]}, False)
            assert server.get(f"/v1/person/{tam['id']}", headers=_headers(person)).status_code == 404
        finally:
            CAMPAIGN_REMOVE_HOOKS[:] = held
