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
