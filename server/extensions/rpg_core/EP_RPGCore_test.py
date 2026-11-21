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
        assert written.status_code in (200, 201), written.text
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
            "picture": None, "updated_at": None, "deleted": False,
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
