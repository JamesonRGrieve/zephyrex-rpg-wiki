# SPDX-License-Identifier: AGPL-3.0-or-later
"""A note's Markdown as the wiki's entry (a Plate value): headings, paragraphs, lists, quotes,
bold, italic and code, and each [[link]] a mention of the record it names, or its text when no
record has that name."""

import re
from typing import Any, Callable, Optional

from vault_import.notes import LINK

# A link's target, resolved: (record type, record id), or none.
Resolve = Callable[[str], Optional[tuple[str, str]]]

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
QUOTE = re.compile(r"^>\s?(.*)$")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
# Bold before italic, so ** isn't read as two *.
MARKS = re.compile(r"(\*\*(?P<bold>[^*]+)\*\*|\*(?P<italic>[^*]+)\*|_(?P<under>[^_]+)_|`(?P<code>[^`]+)`)")


def _marked(text: str) -> list[dict[str, Any]]:
    leaves: list[dict[str, Any]] = []
    at = 0
    for found in MARKS.finditer(text):
        if found.start() > at:
            leaves.append({"text": text[at : found.start()]})
        if found.group("bold") is not None:
            leaves.append({"text": found.group("bold"), "bold": True})
        elif found.group("code") is not None:
            leaves.append({"text": found.group("code"), "code": True})
        else:
            leaves.append({"text": found.group("italic") or found.group("under"), "italic": True})
        at = found.end()
    if at < len(text):
        leaves.append({"text": text[at:]})
    return leaves


def inline(text: str, resolve: Resolve, unresolved: list[str]) -> list[dict[str, Any]]:
    """A line's children: marked text, and a mention for each link that names a record."""
    children: list[dict[str, Any]] = []
    at = 0
    for found in LINK.finditer(text):
        children.extend(_marked(text[at : found.start()]))
        name = found.group(1).strip()
        shown = (found.group(2) or name).strip()
        target = resolve(name)
        if target is None:
            unresolved.append(name)
            children.append({"text": shown})
        else:
            children.append({"type": "mention", "target_entity_type": target[0], "target_entity_id": target[1], "children": [{"text": shown}]})
        at = found.end()
    children.extend(_marked(text[at:]))
    return children or [{"text": ""}]


def to_plate(markdown: str, resolve: Resolve, unresolved: list[str]) -> list[dict[str, Any]]:
    """The entry for ``markdown``; each link no record answers is added to ``unresolved``."""
    blocks: list[dict[str, Any]] = []
    paragraph: list[str] = []
    listing: Optional[dict[str, Any]] = None
    quote: list[str] = []

    def close() -> None:
        nonlocal paragraph, listing, quote
        if paragraph:
            blocks.append({"type": "p", "children": inline(" ".join(paragraph), resolve, unresolved)})
            paragraph = []
        if listing is not None:
            blocks.append(listing)
            listing = None
        if quote:
            blocks.append({"type": "blockquote", "children": inline(" ".join(quote), resolve, unresolved)})
            quote = []

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip() or RULE.match(line):
            close()
            continue
        heading = HEADING.match(line)
        bullet = BULLET.match(line)
        numbered = NUMBERED.match(line)
        quoted = QUOTE.match(line)
        if heading:
            close()
            blocks.append({"type": f"h{len(heading.group(1))}", "children": inline(heading.group(2).strip(), resolve, unresolved)})
        elif bullet or numbered:
            kind = "ul" if bullet else "ol"
            if paragraph or quote or (listing is not None and listing["type"] != kind):
                close()
            if listing is None:
                listing = {"type": kind, "children": []}
            item = (bullet or numbered).group(1)  # type: ignore[union-attr]
            listing["children"].append({"type": "li", "children": inline(item.strip(), resolve, unresolved)})
        elif quoted:
            if paragraph or listing is not None:
                close()
            quote.append(quoted.group(1).strip())
        elif listing is not None and raw.startswith((" ", "\t")):
            # A list item's wrapped line.
            last = listing["children"][-1]
            last["children"].extend(inline(" " + line.strip(), resolve, unresolved))
        else:
            if listing is not None or quote:
                close()
            paragraph.append(line.strip())
    close()
    return blocks
