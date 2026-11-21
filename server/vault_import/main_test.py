# SPDX-License-Identifier: AGPL-3.0-or-later
"""The command in process (--app, --owner), as it runs from a server app's directory, and its refusals."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from rpg_wiki_app import create
from vault_import.__main__ import main
from vault_import.api import Api

FIXTURE = Path(__file__).parent / "fixtures" / "vault"


def test_in_process_it_imports_as_the_owner_and_again_changes_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    server = TestClient(create())
    owner = create_user(server)
    assert main([str(FIXTURE), "--app", "rpg_wiki_app:create", "--owner", str(owner.id), "--setting", "dnd"]) == 0
    assert capsys.readouterr().out.startswith("created: 12, updated: 0")
    mine = Api(server, {"Authorization": f"Bearer {owner.jwt}"})
    assert [row["name"] for row in mine.list("campaign")] == ["The Split Antler"]
    assert main([str(FIXTURE), "--app", "rpg_wiki_app:create", "--owner", str(owner.id), "--setting", "dnd"]) == 0
    assert capsys.readouterr().out.startswith("created: 0, updated: 0, unchanged: 11")


def test_it_needs_one_way_in() -> None:
    with pytest.raises(SystemExit):
        main([str(FIXTURE), "--setting", "dnd"])
    with pytest.raises(SystemExit):
        main([str(FIXTURE), "--app", "rpg_wiki_app:create"])
