# SPDX-License-Identifier: AGPL-3.0-or-later
"""The importer's batched writes (01d51a0) against a real server: link rows queued and made in plural
creates, a refused row reported alone (207), record_metadata one at a time (its create takes one
record), a born record's links made without first reading what it holds, and --default-campaign."""

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create
from vault_import.__main__ import with_default_campaign
from vault_import.api import Api
from vault_import.importer import VAULT_PATH, Importer
from vault_import.notes import read_vault
from vault_import.testing import setting_of

FIXTURE = Path(__file__).parent / "fixtures" / "vault"
pytestmark = pytest.mark.usefixtures("memory_store")


class Recording:
    """The test client, with every request it sends kept: (method, path, query, body)."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.sent: list[tuple[str, str, dict[str, list[str]], Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        for key, value in (kwargs.get("params") or {}).items():
            query.setdefault(key, []).append(str(value))
        self.sent.append((method, parsed.path, query, kwargs.get("json")))
        return self.client.request(method, url, **kwargs)


@pytest.fixture(scope="module")
def server() -> TestClient:
    return TestClient(create())


def _api(server: TestClient) -> tuple[Api, Recording]:
    user = create_user(server)
    recording = Recording(server)
    api = Api(recording, {"Authorization": f"Bearer {user.jwt}"})  # type: ignore[arg-type]
    return api, recording


def _vault(root: Path, notes: dict[str, str]) -> Path:
    for path, text in notes.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    return root


def _hooks(campaign: str, **depends: str) -> dict[str, str]:
    return {
        f"Hooks/{name}.md": f"---\nentity_type: hook\nname: {name}\ncampaign: {campaign}\n{extra}---\nA thread.\n"
        for name, extra in depends.items()
    }


def test_a_new_records_links_are_made_without_reading_what_it_holds(server: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Records this run made hold nothing yet: until the queued links are written, no GET of their
    tags, statuses, ties or properties (the campaigns are settled and checked after that, and the
    one-row plural probe per resource is not a read of a record), and each link resource is written
    in plural creates, not one POST a row."""
    api, recording = _api(server)
    flushed_at: list[int] = []
    flush = Importer._flush_pending

    def counted(self: Importer) -> None:
        flushed_at.append(len(recording.sent))
        flush(self)

    monkeypatch.setattr(Importer, "_flush_pending", counted)
    report = Importer(api, setting_slug=setting_of(api, "fixture-fantasy")).run(read_vault(FIXTURE))
    assert report.refused == [], report.refused
    link_reads = [
        (path, query)
        for method, path, query, _body in recording.sent[: flushed_at[0]]
        if method == "GET"
        and path in ("/v1/entity_taxon", "/v1/entity_status", "/v1/relationship", "/v1/disposition", "/v1/hook_dependency", "/v1/record_metadata/of")
        and query != {"limit": ["1"]}
    ]
    assert link_reads == []
    plural = {path for method, path, _query, body in recording.sent if method == "POST" and isinstance(body, dict) and any(isinstance(v, list) for v in body.values())}
    assert {"/v1/entity_taxon", "/v1/disposition"} <= plural, plural


def test_record_metadata_goes_one_at_a_time_and_a_born_records_property_once(server: TestClient) -> None:
    """record_metadata's create takes one record: create_batch falls back to one POST each. A born
    record's vault path is asked for twice (when it is made and when it is linked) and written once."""
    api, recording = _api(server)
    report = Importer(api, setting_slug=setting_of(api, "fixture-fantasy")).run(read_vault(FIXTURE))
    assert report.refused == [], report.refused
    singles = [body for method, path, _query, body in recording.sent if method == "POST" and path == "/v1/record_metadata" and "record_metadata" in (body or {})]
    assert singles, "no single record_metadata creates"
    [campaign] = [row for row in api.list("campaign") if row["name"] == "The Split Antler"]
    holst = next(row for row in api.list("person", campaign_id=campaign["id"]) if row["name"] == "Holst")
    keys = [row["key"] for row in api.properties("person", str(holst["id"]))]
    assert keys.count(VAULT_PATH) == 1, keys


def test_a_hook_named_from_both_ends_is_one_dependency(server: TestClient, tmp_path: Path) -> None:
    """A quest that depends on an objective, and the objective that names the quest as its parent, are
    the same edge: queued once, so the run refuses nothing."""
    notes = _hooks("Both Ends", **{"Free the Valley": "depends_on: ['[[Open the Gate]]']\n", "Open the Gate": "parent_hook: '[[Free the Valley]]'\n"})
    api, _recording = _api(server)
    report = Importer(api, setting_slug=setting_of(api, "fixture-fantasy")).run(read_vault(_vault(tmp_path, notes)))
    assert report.refused == [], report.refused
    [campaign] = [row for row in api.list("campaign") if row["name"] == "Both Ends"]
    hooks = {row["name"]: str(row["id"]) for row in api.list("hook", campaign_id=campaign["id"])}
    edges = api.list("hook_dependency", parent_hook_id=hooks["Open the Gate"], child_hook_id=hooks["Free the Valley"])
    assert len(edges) == 1


def test_a_refused_row_in_a_batch_is_reported_alone_and_the_rest_are_made(server: TestClient, tmp_path: Path) -> None:
    """Two hooks that wait on each other: the server's cycle guard refuses the second edge (a 207 row
    error), which is reported against its note; the batch's other edges are written."""
    notes = _hooks(
        "Loop",
        **{"First": "depends_on: ['[[Second]]']\n", "Second": "depends_on: ['[[First]]']\n", "Third": "depends_on: ['[[First]]']\n"},
    )
    api, recording = _api(server)
    report = Importer(api, setting_slug=setting_of(api, "fixture-fantasy")).run(read_vault(_vault(tmp_path, notes)))
    assert len(report.refused) == 1, report.refused
    path, why = report.refused[0]
    assert path in ("Hooks/First.md", "Hooks/Second.md") and why.startswith("prerequisite "), report.refused
    assert any(method == "POST" and path == "/v1/hook_dependency" and "hook_dependencies" in (body or {}) for method, path, _q, body in recording.sent)
    [campaign] = [row for row in api.list("campaign") if row["name"] == "Loop"]
    hooks = {row["name"]: str(row["id"]) for row in api.list("hook", campaign_id=campaign["id"])}
    assert api.list("hook_dependency", parent_hook_id=hooks["First"], child_hook_id=hooks["Third"])
    made = [edge for edge in (api.list("hook_dependency", parent_hook_id=hooks[a], child_hook_id=hooks[b]) for a, b in (("Second", "First"), ("First", "Second"))) if edge]
    assert len(made) == 1


def test_default_campaign_fills_only_notes_that_name_none_and_are_not_setting_wide(tmp_path: Path) -> None:
    notes = read_vault(
        _vault(
            tmp_path,
            {
                "Root.md": "---\nentity_type: location\nname: Root\n---\nHere.\n",
                "Named.md": "---\nentity_type: location\nname: Named\ncampaign: Elsewhere\n---\nThere.\n",
                "Canon.md": "---\nentity_type: location\nname: Canon\nsetting_wide: true\n---\nEverywhere.\n",
            },
        )
    )
    with_default_campaign(notes, "Home Run")
    assert {note.name: note.meta.get("campaign") for note in notes} == {"Root": "Home Run", "Named": "Elsewhere", "Canon": None}
