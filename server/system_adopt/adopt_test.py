# SPDX-License-Identifier: AGPL-3.0-or-later
"""System-level content (operator, 2026-11-25: "The out of the box scenarios, pregens, everything
with the SRD should also be system level down to campaigns which are user level"): a system import
writes SYSTEM's content, which every account reads and plays a copy of and only the server changes;
an account's existing copy is adopted in place, and another's merged into it."""

import time
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from zephyrex.lib.Environment import env
from zephyrex.logic.BLL_Auth import UserManager
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create
from vault_import.api import Api
from vault_import.importer import Importer
from vault_import.notes import read_vault
from vault_import.testing import setting_of

# The fixture vault's Holst.png is uploaded as his picture.
pytestmark = pytest.mark.usefixtures("memory_store")

FIXTURE = Path(__file__).resolve().parents[1] / "vault_import" / "fixtures" / "vault"
SCENARIO = "The Split Antler"


@pytest.fixture(scope="module")
def server() -> TestClient:
    return TestClient(create())


def _registry(server: TestClient) -> Any:
    return server.app.state.model_registry  # type: ignore[attr-defined]


def _as(server: TestClient, user: Any) -> Api:
    return Api(server, {"Authorization": f"Bearer {user.jwt}"})


def _system(server: TestClient) -> Api:
    """The API as SYSTEM, as vault_import --system signs in (connect.in_process)."""
    registry = _registry(server)
    user = UserManager(requester_id=env("ROOT_ID"), model_registry=registry).get(id=env("SYSTEM_ID"))
    token = UserManager.generate_jwt_token(user_id=str(user.id), email=str(user.email), expiration_hours=1, model_registry=registry)
    api = Api(server, {"Authorization": f"Bearer {token}"})
    api.owner_id = str(user.id)
    api.system = True
    api.also_mine = {str(env("TEMPLATE_ID"))}
    api.model_registry = registry  # type: ignore[attr-defined]
    return api


def _headers(user: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {user.jwt}"}


def _scenario_of(api: Api, setting_slug: str) -> dict[str, Any]:
    setting = next(row for row in api.list("setting") if row["slug"] == setting_slug)
    [found] = [row for row in api.list("campaign", setting_id=setting["id"]) if row["name"] == SCENARIO and row.get("is_scenario") and not row.get("scenario_id")]
    return found


def _start(server: TestClient, user: Any, scenario_id: str) -> dict[str, Any]:
    """A start followed to its end; its playthrough, as its starter reads it."""
    accepted = server.post(f"/v1/campaign/{scenario_id}/instantiate", json={"instantiate": {}}, headers=_headers(user))
    assert accepted.status_code == 202, accepted.text
    start = accepted.json()["start"]
    deadline = time.monotonic() + 60
    while start["state"] == "running":
        assert time.monotonic() < deadline, start
        time.sleep(0.5)
        start = server.get(f"/v1/campaign_start/{start['id']}", headers=_headers(user)).json()["campaign_start"]
    assert start["state"] == "done", start
    campaign: dict[str, Any] = server.get(f"/v1/campaign/{start['campaign_id']}", headers=_headers(user)).json()["campaign"]
    return campaign


def test_a_system_import_is_every_accounts_to_read_and_play_and_the_servers_to_change(server: TestClient) -> None:
    system = _system(server)
    slug = f"srd-{uuid.uuid4().hex[:8]}"
    owner = create_user(server)
    mine = _as(server, owner)
    own = setting_of(mine, f"own-{uuid.uuid4().hex[:8]}")
    # An account's own copy of the same vault, imported first: the system import never touches it.
    assert Importer(mine, setting_slug=own).run(read_vault(FIXTURE)).refused == []
    theirs = _scenario_of(mine, own)

    first = Importer(system, setting_slug=slug, setting_name="Fixture SRD").run(read_vault(FIXTURE))
    assert first.refused == [], first.refused
    assert "setting Fixture SRD" in first.created and f"campaign {SCENARIO}" in first.created
    scenario = _scenario_of(system, slug)
    # The operator, 2026-11-25: one shared copy, "template user owned": the import writes as SYSTEM
    # and makes the setting the template account's.
    assert scenario["created_by_user_id"] == env("TEMPLATE_ID")
    assert first.shared and "made system level" in first.shared[0], first.shared
    assert scenario["id"] != theirs["id"]
    held = mine.get("campaign", theirs["id"])[0]
    assert (held["created_by_user_id"], held["updated_at"]) == (owner.id, theirs["updated_at"])
    # A second run matches SYSTEM's own rows only, so it makes and changes nothing.
    again = Importer(system, setting_slug=slug).run(read_vault(FIXTURE))
    assert (again.created, again.refused) == ([], []), again.created
    # And SYSTEM still changes the shared copy: a forced re-import writes it, and it stays TEMPLATE's.
    forced = Importer(system, setting_slug=slug, force=True).run(read_vault(FIXTURE))
    assert (forced.created, forced.refused) == ([], []) and forced.updated, (forced.created, forced.refused)
    assert _scenario_of(system, slug)["created_by_user_id"] == env("TEMPLATE_ID")

    # The setting decides the level, both ways.
    with pytest.raises(ValueError, match="isn't yours"):
        Importer(mine, setting_slug=slug).run(read_vault(FIXTURE))
    with pytest.raises(ValueError, match="an account's own"):
        Importer(system, setting_slug=own).run(read_vault(FIXTURE))

    # Every account reads it and plays a copy of it; no account writes it.
    reader = create_user(server)
    seen = [row["id"] for row in _as(server, reader).list("campaign") if row.get("is_scenario")]
    assert scenario["id"] in seen
    holst = next(row for row in _as(server, reader).list("person", campaign_id=scenario["id"]) if row["name"] == "Holst")
    etag = server.get(f"/v1/person/{holst['id']}", headers=_headers(reader)).headers.get("etag", "")
    assert server.put(f"/v1/person/{holst['id']}", json={"person": {"description": "Mine now."}}, headers={**_headers(reader), "If-Match": etag}).status_code in (403, 404)
    setting_id = scenario["setting_id"]
    into = server.post("/v1/person", json={"person": {"name": "Stowaway", "campaign_id": scenario["id"], "setting_id": setting_id}}, headers=_headers(reader))
    assert into.status_code == 403, into.text
    canon = server.post("/v1/person", json={"person": {"name": "Squatter", "setting_id": setting_id}}, headers=_headers(reader))
    assert canon.status_code == 403, canon.text
    # A campaign of the reader's own in it is theirs (campaigns are user level).
    assert server.post("/v1/campaign", json={"campaign": {"name": "My Table", "setting_id": setting_id}}, headers=_headers(reader)).status_code == 201
    run = _start(server, reader, scenario["id"])
    assert (run["created_by_user_id"], run["scenario_id"], run["is_scenario"]) == (reader.id, scenario["id"], False)
    copies = _as(server, reader).list("person", campaign_id=run["id"])
    assert {row["name"] for row in copies} >= {"Holst", "Dingus"}
    assert {row["created_by_user_id"] for row in copies} == {reader.id}


def test_an_accounts_copy_is_adopted_in_place_and_anothers_merged_into_it(server: TestClient) -> None:
    registry = _registry(server)
    from zephyrex.extensions.rpg_core.SystemAdopt import ADOPT_HOOKS, adopt_settings  # type: ignore[import-not-found]

    a, b, reader = create_user(server), create_user(server), create_user(server)
    sides: dict[str, dict[str, Any]] = {}
    for name, user in (("a", a), ("b", b)):
        api = _as(server, user)
        slug = setting_of(api, f"adopt-{name}-{uuid.uuid4().hex[:8]}")
        assert Importer(api, setting_slug=slug).run(read_vault(FIXTURE)).refused == []
        scenario = _scenario_of(api, slug)
        setting_id = scenario["setting_id"]
        # Canon (the setting's, no campaign) a scenario's record links to: a start shares it.
        guild = api.create("faction", name="Old Guild", setting_id=setting_id)
        holst = next(row for row in api.list("person", campaign_id=scenario["id"]) if row["name"] == "Holst")
        api.create("relationship", person_id=holst["id"], target_faction_id=guild["id"], kind="member_of")
        sides[name] = {"user": user, "api": api, "slug": slug, "scenario": scenario, "setting_id": setting_id, "guild": guild}
    only = sides["b"]["api"].create("person", name="Only In B", kind="npc", campaign_id=sides["b"]["scenario"]["id"], setting_id=sides["b"]["setting_id"])
    for side in sides.values():
        side["run"] = _start(server, side["user"], side["scenario"]["id"])
        copied = next(row for row in side["api"].list("person", campaign_id=side["run"]["id"]) if row["name"] == "Holst")
        # The copy's own link to the shared canon guild (beside the vault's to the Circle Compact).
        [side["link"]] = [row for row in side["api"].list("relationship", person_id=copied["id"]) if row.get("target_faction_id") == side["guild"]["id"]]

    seen: list[tuple[str, list[str], dict[str, str], bool]] = []

    def vtt(model_registry: Any, setting_id: str, scenario_ids: list[str], id_map: dict[str, str], dry_run: bool) -> str:
        seen.append((setting_id, scenario_ids, id_map, dry_run))
        return "vtt: nothing of its own here"

    ADOPT_HOOKS.append(vtt)
    try:
        dry = adopt_settings(registry, [sides["a"]["slug"], sides["b"]["slug"]], dry_run=True)
        assert sides["a"]["api"].get("campaign", sides["a"]["scenario"]["id"])[0]["created_by_user_id"] == a.id
        assert sides["b"]["api"].get("campaign", sides["b"]["scenario"]["id"])[0]["id"] == sides["b"]["scenario"]["id"]
        assert "Only In B" in dry[1].line() and dry[1].removed.get("campaigns") == 1, dry[1].line()
        seen.clear()
        done = adopt_settings(registry, [sides["a"]["slug"], sides["b"]["slug"]], dry_run=False)
    finally:
        ADOPT_HOOKS.remove(vtt)
    assert done[0].adopted["campaigns"] == 1 and done[0].adopted["settings"] == 1, done[0].line()
    assert "vtt: nothing of its own here" in done[1].hooks
    scenario, setting_id = sides["a"]["scenario"], sides["a"]["setting_id"]
    assert [(one[0], one[3]) for one in seen] == [(setting_id, False), (setting_id, False)]
    assert seen[1][2][sides["b"]["scenario"]["id"]] == scenario["id"]

    # A's copy is TEMPLATE's in place: every account reads it, ids unchanged.
    as_reader = _as(server, reader)
    adopted = as_reader.get("campaign", scenario["id"])[0]
    assert adopted["created_by_user_id"] == env("TEMPLATE_ID")
    people = as_reader.list("person", campaign_id=scenario["id"])
    names = [row["name"] for row in people]
    assert len(names) == len(set(names)) and "Only In B" in names, names
    assert {row["created_by_user_id"] for row in people} == {env("TEMPLATE_ID")}
    assert as_reader.get("faction", sides["a"]["guild"]["id"])[0]["created_by_user_id"] == env("TEMPLATE_ID")
    assert as_reader.get("person", only["id"])[0]["campaign_id"] == scenario["id"]

    # A's playthrough is still A's, its link to the canon guild too.
    run_a = sides["a"]["api"].get("campaign", sides["a"]["run"]["id"])[0]
    assert (run_a["created_by_user_id"], run_a["scenario_id"]) == (a.id, scenario["id"])
    assert sides["a"]["api"].get("relationship", sides["a"]["link"]["id"])[0]["created_by_user_id"] == a.id

    # B's playthrough is B's, now of the system scenario, in the system setting, linked to its guild.
    run_b = sides["b"]["api"].get("campaign", sides["b"]["run"]["id"])[0]
    assert (run_b["created_by_user_id"], run_b["scenario_id"], run_b["setting_id"]) == (b.id, scenario["id"], setting_id)
    link_b = sides["b"]["api"].get("relationship", sides["b"]["link"]["id"])[0]
    assert (link_b["created_by_user_id"], link_b["target_faction_id"]) == (b.id, sides["a"]["guild"]["id"])
    # B's duplicates are gone.
    assert server.get(f"/v1/campaign/{sides['b']['scenario']['id']}", headers=_headers(b)).status_code == 404
    assert server.get(f"/v1/faction/{sides['b']['guild']['id']}", headers=_headers(b)).status_code == 404
    assert sides["b"]["slug"] not in {row["slug"] for row in sides["b"]["api"].list("setting")}
    # Nobody but the server changes it now, A included.
    holst = next(row for row in people if row["name"] == "Holst")
    etag = server.get(f"/v1/person/{holst['id']}", headers=_headers(a)).headers.get("etag", "")
    assert server.put(f"/v1/person/{holst['id']}", json={"person": {"description": "Mine still?"}}, headers={**_headers(a), "If-Match": etag}).status_code in (403, 404)


def test_the_accounts_copies_inside_one_setting_are_merged_into_one(server: TestClient) -> None:
    """Zephyrex RPG, 2026-11-25: on prod four accounts' vault_imports each wrote the scenarios into
    one setting, so adopting it alone would share four copies of each. --merge-copies keeps one
    author's copy (--keep-owner) and merges every other author's into it inside the setting."""
    registry = _registry(server)
    from sqlalchemy import update

    from zephyrex.extensions.rpg_core.SystemAdopt import _every_table, adopt_settings  # type: ignore[import-not-found]

    a, b, reader = create_user(server), create_user(server), create_user(server)
    mine, theirs = _as(server, a), _as(server, b)
    slug = setting_of(mine, f"inside-{uuid.uuid4().hex[:8]}")
    other = setting_of(theirs, f"inside-b-{uuid.uuid4().hex[:8]}")
    assert Importer(mine, setting_slug=slug).run(read_vault(FIXTURE)).refused == []
    assert Importer(theirs, setting_slug=other).run(read_vault(FIXTURE)).refused == []
    kept, copy = _scenario_of(mine, slug), _scenario_of(theirs, other)
    run_b = _start(server, b, copy["id"])
    # B's copy moved into A's setting, as prod's imports left it.
    session = registry.DB.session()
    try:
        for table in _every_table(registry):
            if "setting_id" in table.c:
                session.execute(update(table).where(table.c.setting_id == copy["setting_id"]).values(setting_id=kept["setting_id"]))
        session.commit()
    finally:
        session.close()
    from zephyrex.extensions.rpg_core.SystemAdopt import _clear_cache  # type: ignore[import-not-found]

    _clear_cache({table.name for table in _every_table(registry)})

    dry = adopt_settings(registry, [slug], dry_run=True, merge_copies=True, keep_owner=str(a.id))
    assert len(dry) == 2 and f"{b.id}'s copy" in dry[0].line() and dry[0].removed.get("campaigns") == 1, dry[0].line()
    assert theirs.get("campaign", copy["id"])[0]["created_by_user_id"] == b.id

    done = adopt_settings(registry, [slug], dry_run=False, merge_copies=True, keep_owner=str(a.id))
    assert done[0].removed.get("campaigns") == 1 and done[1].adopted.get("campaigns") == 1, [one.line() for one in done]
    as_reader = _as(server, reader)
    scenarios = [row for row in as_reader.list("campaign", setting_id=kept["setting_id"]) if row.get("is_scenario") and not row.get("scenario_id")]
    assert [row["id"] for row in scenarios if row["name"] == SCENARIO] == [kept["id"]]
    assert scenarios[0]["created_by_user_id"] == env("TEMPLATE_ID")
    people = as_reader.list("person", campaign_id=kept["id"])
    names = [row["name"] for row in people]
    assert len(names) == len(set(names)) and "Holst" in names, names
    assert {row["created_by_user_id"] for row in people} == {env("TEMPLATE_ID")}
    # B's copy is gone, and B's playthrough is now of the one shared scenario, still B's.
    assert server.get(f"/v1/campaign/{copy['id']}", headers=_headers(b)).status_code == 404
    run = theirs.get("campaign", run_b["id"])[0]
    assert (run["created_by_user_id"], run["scenario_id"], run["setting_id"]) == (b.id, kept["id"], kept["setting_id"])


def test_records_match_by_kind_and_fall_back_to_the_primarys_canon() -> None:
    """Zephyrex RPG, 2026-11-25 (prod's dry run listed each tester's race and place taxa as
    unmatched): a taxon is made per scope, kind and name, so a copy's "Pregen" tag finds the
    primary's tag, not its category; and a scenario's taxon with no twin in the primary's
    scenario finds the primary's canon one of its kind and name."""
    from types import SimpleNamespace as Row

    from zephyrex.extensions.rpg_core.SystemAdopt import Held, _match  # type: ignore[import-not-found]

    taxa = object()

    def held(setting: str, scenario: str, rows: list[Row]) -> Held:
        return Held(setting=Row(id=setting), scenarios=[Row(id=scenario, name="The Split Antler")], records=[(taxa, rows)], dependents=[])

    primary = held("s", "p", [
        Row(id="p-tag", name="Pregen", kind="tag", campaign_id="p"),
        Row(id="p-cat", name="Pregen", kind="category", campaign_id="p"),
        Row(id="p-orc", name="Orc", kind="race", campaign_id=None),
    ])
    copy = held("s", "c", [
        Row(id="c-cat", name="Pregen", kind="category", campaign_id="c"),
        Row(id="c-tag", name="Pregen", kind="tag", campaign_id="c"),
        Row(id="c-orc", name="Orc", kind="race", campaign_id="c"),
        Row(id="c-new", name="Owlbear", kind="race", campaign_id="c"),
    ])
    id_map, unmatched = _match(primary, copy)
    assert (id_map["c"], id_map["c-cat"], id_map["c-tag"], id_map["c-orc"]) == ("p", "p-cat", "p-tag", "p-orc")
    assert [row.id for _manager, row in unmatched] == ["c-new"]


def test_what_one_copy_moved_in_is_matched_by_the_next() -> None:
    """Zephyrex RPG, 2026-11-25: each tester's newer copy had an Orc the kept copy lacked; the
    first copy's moves in, and the next copies' Orcs match it, so one Orc, not three."""
    from types import SimpleNamespace as Row

    from zephyrex.extensions.rpg_core.SystemAdopt import Held, _join, _match  # type: ignore[import-not-found]

    taxa = object()

    def held(scenario: str, rows: list[Row]) -> Held:
        return Held(setting=Row(id="s"), scenarios=[Row(id=scenario, name="Goblin Ambush")], records=[(taxa, rows)], dependents=[])

    kept = held("k", [])
    first, second = held("a", [Row(id="a-orc", name="Orc", kind="race", campaign_id="a")]), held("b", [Row(id="b-orc", name="Orc", kind="race", campaign_id="b")])
    id_map, unmatched = _match(kept, first)
    assert [row.id for _manager, row in unmatched] == ["a-orc"]
    _join(kept, first, id_map, set(id_map), unmatched)
    id_map, unmatched = _match(kept, second)
    assert (id_map["b-orc"], unmatched) == ("a-orc", [])


def test_drop_unmatched_removes_an_older_copys_leftovers(server: TestClient) -> None:
    """--drop-unmatched (Zephyrex RPG, 2026-11-25: the operator's copy is of an older vault): a
    merged copy's scenario records with no match in the kept copy are removed, not moved in; its
    canon with no match moves in all the same (2026-11-26: prod's SRD canon is the operator's alone,
    and the kept copy has none), with what hangs on it."""
    registry = _registry(server)
    from sqlalchemy import update

    from zephyrex.extensions.rpg_core.SystemAdopt import _clear_cache, _every_table, adopt_settings  # type: ignore[import-not-found]

    a, b = create_user(server), create_user(server)
    mine, theirs = _as(server, a), _as(server, b)
    slug = setting_of(mine, f"drop-{uuid.uuid4().hex[:8]}")
    other = setting_of(theirs, f"drop-b-{uuid.uuid4().hex[:8]}")
    assert Importer(mine, setting_slug=slug).run(read_vault(FIXTURE)).refused == []
    assert Importer(theirs, setting_slug=other).run(read_vault(FIXTURE)).refused == []
    kept, copy = _scenario_of(mine, slug), _scenario_of(theirs, other)
    stale = theirs.create("person", name="Only In The Old Vault", kind="npc", campaign_id=copy["id"], setting_id=copy["setting_id"])
    canon = theirs.create("faction", name="Only In The Copy's Canon", setting_id=copy["setting_id"])
    holst = next(row for row in theirs.list("person", campaign_id=copy["id"]) if row["name"] == "Holst")
    theirs.create("relationship", person_id=holst["id"], target_faction_id=canon["id"], kind="member_of")
    session = registry.DB.session()
    try:
        for table in _every_table(registry):
            if "setting_id" in table.c:
                session.execute(update(table).where(table.c.setting_id == copy["setting_id"]).values(setting_id=kept["setting_id"]))
        session.commit()
    finally:
        session.close()
    _clear_cache({table.name for table in _every_table(registry)})

    done = adopt_settings(registry, [slug], dry_run=False, merge_copies=True, keep_owner=str(a.id), drop_unmatched=True)
    assert "Only In The Old Vault" in done[0].line() and "dropped (no match)" in done[0].line(), done[0].line()
    names = [row["name"] for row in _as(server, create_user(server)).list("person", campaign_id=kept["id"])]
    assert "Only In The Old Vault" not in names and len(names) == len(set(names)), names
    assert server.get(f"/v1/person/{stale['id']}", headers=_headers(b)).status_code == 404
    kept_canon = _as(server, create_user(server)).get("faction", canon["id"])[0]
    assert (kept_canon["created_by_user_id"], kept_canon["setting_id"]) == (env("TEMPLATE_ID"), kept["setting_id"])
    assert "Only In The Copy's Canon" not in done[0].line().split("dropped (no match)")[-1]
    # The kept copy's Holst now carries the copy's link to that canon faction.
    kept_holst = next(row for row in mine.list("person", campaign_id=kept["id"]) if row["name"] == "Holst")
    assert any(row.get("target_faction_id") == canon["id"] for row in theirs.list("relationship", person_id=kept_holst["id"]))
