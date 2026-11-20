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
