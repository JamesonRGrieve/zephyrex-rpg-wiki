# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core and world_spatial against a real server, the same rules as the lite edition's
(client/src/app/api/v1/routes.test.ts): a world, places in a tree with kinds from the contract and
no cycles, people with a kind, a world and a place, entries kept with their plain text, and one
person's records invisible to another."""

import json
from collections.abc import Iterator
from typing import Any

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
            "keywords": [], "voice": None, "lore": None, "provenance": "homebrew", "source": None, "gm_only": False,
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
        # The seeded Fallout holds "fallout", so a person's own takes the next number.
        own = _create(server, person, "setting", name="Fallout")
        assert own["slug"] == "fallout-2"
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
        forty_k = seeded["warhammer-40000"]
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

        response = server.post(f"/v1/campaign/{scenario['id']}/instantiate", json={"instantiate": {"name": "The Flicker, run 1"}}, headers=_headers(person))
        assert response.status_code == 201, response.text
        started = response.json()
        run, ids = started["campaign"], started["id_map"]
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
