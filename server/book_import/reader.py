# SPDX-License-Identifier: AGPL-3.0-or-later
"""A stitched book: its header (<!-- book: slug | line: dh2 | pages: N | … -->), its title (the
first # heading) and its pages (<!-- page p0001 -->), each page's markdown as entry blocks."""

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

HEADER = re.compile(r"<!--\s*book:\s*(?P<fields>.*?)-->")
PAGE = re.compile(r"^<!--\s*page\s+p(?P<number>\d+)\s*-->\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
TAG = re.compile(r"<[^>]+>")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass
class Book:
    slug: str
    line: Optional[str]
    title: str
    pages: list[tuple[int, list[dict[str, Any]]]]


def _paragraph(text: str) -> dict[str, Any]:
    return {"type": "p", "children": [{"text": text}]}


def _tables_as_text(text: str) -> str:
    """An HTML table as lines of cells joined by " | " (what a passage can say of it)."""

    def table(match: re.Match[str]) -> str:
        rows = []
        for row in ROW.findall(match.group(0)):
            cells = [html.unescape(TAG.sub("", cell)).strip() for cell in CELL.findall(row)]
            if any(cells):
                rows.append(" | ".join(cells))
        return "\n\n".join(rows)

    return re.sub(r"<table.*?</table>", table, text, flags=re.IGNORECASE | re.DOTALL)


def page_blocks(markdown: str) -> list[dict[str, Any]]:
    """A page's markdown as entry blocks: headings as h1-h6, each paragraph (lines up to a blank) a p."""
    text = _tables_as_text(COMMENT.sub("", markdown))
    blocks: list[dict[str, Any]] = []
    lines: list[str] = []

    def close() -> None:
        joined = " ".join(line.strip() for line in lines if line.strip())
        if joined:
            blocks.append(_paragraph(html.unescape(TAG.sub("", joined))))
        lines.clear()

    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            close()
            blocks.append({"type": f"h{len(heading.group(1))}", "children": [{"text": heading.group(2).strip("# ")}]})
        elif not line.strip():
            close()
        else:
            lines.append(line)
    close()
    return blocks


def read_book(path: Path) -> Book:
    text = path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    header = HEADER.search(text[:2000])
    if header:
        parts = [part.strip() for part in header.group("fields").split("|")]
        fields["slug"] = parts[0]
        for part in parts[1:]:
            key, _, value = part.partition(":")
            fields[key.strip()] = value.strip()
    title = next((match.group(2).strip() for line in text.splitlines()[:20] if (match := HEADING.match(line)) and len(match.group(1)) == 1), None)
    pages: list[tuple[int, list[dict[str, Any]]]] = []
    number: Optional[int] = None
    held: list[str] = []
    for line in text.splitlines():
        found = PAGE.match(line)
        if found:
            if number is not None:
                pages.append((number, page_blocks("\n".join(held))))
            number, held = int(found.group("number")), []
        elif number is not None:
            held.append(line)
    if number is not None:
        pages.append((number, page_blocks("\n".join(held))))
    return Book(slug=fields.get("slug") or path.stem, line=fields.get("line"), title=title or path.stem.replace("-", " ").title(), pages=pages)
