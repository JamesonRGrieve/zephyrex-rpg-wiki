# SPDX-License-Identifier: AGPL-3.0-or-later
"""A short Markdown body as an entry (contract/markdown-entry-cases.json; the client's
lib/markdownEntry.ts computes the same): headings, bulleted lists and paragraphs, text as written."""

import re
from typing import Any

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^[-*]\s+(.*)$")


def markdown_entry(markdown: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    paragraph: list[str] = []
    items: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append({"type": "p", "children": [{"text": " ".join(paragraph)}]})
            paragraph.clear()
        if items:
            blocks.append({"type": "ul", "children": [{"type": "li", "children": [{"text": item}]} for item in items]})
            items.clear()

    for raw in (markdown or "").splitlines():
        line = raw.strip()
        heading, bullet = HEADING.match(line), BULLET.match(line)
        if not line:
            flush()
        elif heading:
            flush()
            blocks.append({"type": f"h{len(heading.group(1))}", "children": [{"text": heading.group(2).strip()}]})
        elif bullet:
            if paragraph:
                flush()
            items.append(bullet.group(1).strip())
        else:
            if items:
                flush()
            paragraph.append(line)
    flush()
    return blocks
