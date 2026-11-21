# SPDX-License-Identifier: AGPL-3.0-or-later
"""A note's Markdown as the wiki's entry, checked by the server's own entry rules."""

from typing import Optional

from vault_import.markdown import to_plate
from zephyrex.extensions.wiki_shared.Entry import checked, plain_text  # type: ignore[import-not-found]

KNOWN = {"Holst": ("person", "p1"), "Brindlemarsh Stable": ("location", "l2")}


def resolve(name: str) -> Optional[tuple[str, str]]:
    return KNOWN.get(name)


def test_blocks_marks_and_links() -> None:
    unresolved: list[str] = []
    markdown = "## History\n\nBought the **stable** from [[Holst]]'s uncle,\na *long* time ago.\n\n- One [[Nowhere]]\n- Two\n\n1. First\n\n> [[Brindlemarsh Stable|The stable]] smells.\n\n---\n"
    entry = to_plate(markdown, resolve, unresolved)
    assert [block["type"] for block in entry] == ["h2", "p", "ul", "ol", "blockquote"]
    paragraph = entry[1]["children"]
    assert {"text": "stable", "bold": True} in paragraph
    assert {"text": "long", "italic": True} in paragraph
    mention = next(child for child in paragraph if child.get("type") == "mention")
    assert (mention["target_entity_type"], mention["target_entity_id"], mention["children"]) == ("person", "p1", [{"text": "Holst"}])
    assert entry[4]["children"][0]["children"] == [{"text": "The stable"}]
    assert unresolved == ["Nowhere"]
    # The server takes it as it is: every node an element with children or a text leaf.
    assert checked(entry) == entry
    assert plain_text(entry).splitlines()[0] == "History"


def test_an_empty_note_is_an_empty_entry() -> None:
    assert to_plate("\n\n", resolve, []) == []
