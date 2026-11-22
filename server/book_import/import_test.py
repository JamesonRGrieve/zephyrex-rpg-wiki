# SPDX-License-Identifier: AGPL-3.0-or-later
"""Placeholder books (never real book text) into the lore index, found by lore_search in scope."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from zephyrex.testing.factories import create_user

from book_import.__main__ import books_in, main, EXCLUDE
from book_import.reader import read_book
from rpg_wiki_app import create
from vault_import.api import Api

BOOKS = Path(__file__).parent / "fixtures" / "books"
CORE = BOOKS / "dh2" / "placeholder-core-rulebook.md"


def test_a_stitched_book_reads_as_pages_of_blocks() -> None:
    book = read_book(CORE)
    assert (book.slug, book.line, book.title) == ("placeholder-core-rulebook", "dh2", "Placeholder Core Rulebook")
    assert [page for page, _blocks in book.pages] == [1, 2]
    first = book.pages[0][1]
    assert first[0] == {"type": "h2", "children": [{"text": "Chapter One: The Hollow Spire"}]}
    texts = [block["children"][0]["text"] for block in first[1:]]
    assert texts[1:] == ["Bell | Hour", "Brass | Dawn"]
    # Sheets, handouts and screens are left out by default.
    assert [one.name for one in books_in([BOOKS], EXCLUDE)] == ["placeholder-core-rulebook.md"]


def test_books_land_in_their_settings_canon_and_only_there(capsys: pytest.CaptureFixture[str]) -> None:
    from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

    server = TestClient(create())
    owner = create_user(server)
    api = Api(server, {"Authorization": f"Bearer {owner.jwt}"})
    args = [str(BOOKS), "--setting", "dnd", "--app", "rpg_wiki_app:create", "--owner", str(owner.id)]
    # The wiki alone serves no game systems: without --unscoped a book is skipped, and says why.
    assert main(args) == 0
    assert "skipped placeholder-core-rulebook: no game system 'dark-heresy-2e'" in capsys.readouterr().out
    assert main([*args, "--unscoped", "--dry-run"]) == 0
    assert "would import placeholder-core-rulebook: 2 pages" in capsys.readouterr().out
    assert main([*args, "--unscoped"]) == 0
    first = capsys.readouterr().out
    assert "imported placeholder-core-rulebook: 2 pages" in first and "character-sheet" not in first

    dnd = next(row for row in api.list("setting") if row["slug"] == "dnd")
    other = api.create("setting", name="Book-less Setting")
    inside = api.create("campaign", name="Spire Run", setting_id=dnd["id"])
    outside = api.create("campaign", name="Elsewhere Run", setting_id=other["id"])
    registry = server.app.state.model_registry  # type: ignore[attr-defined]
    search = loaded_ability(registry, "rpg_core", "lore_search")
    assert search is not None
    found = search(registry, str(owner.id), inside["id"], "the hollow spire bells ring for tithes")["passages"]
    page = next(one for one in found if one["record_type"] == "book")
    assert (page["source"], page["page"], page["path"]) == ("Placeholder Core Rulebook", 1, ["Placeholder Core Rulebook", "Chapter One: The Hollow Spire"])
    assert not [one for one in search(registry, str(owner.id), outside["id"], "the hollow spire bells ring")["passages"] if one["record_type"] == "book"]
    # Imported again: replaced, not doubled.
    assert main([*args, "--unscoped"]) == 0
    capsys.readouterr()
    again = [one for one in search(registry, str(owner.id), inside["id"], "hollow spire sump wardens lanterns", k=50)["passages"] if one["record_type"] == "book"]
    assert len(again) == len({(one["page"], one["text"]) for one in again}) and len(again) >= 2
