# SPDX-License-Identifier: AGPL-3.0-or-later
"""Foundry's HTML text as Markdown the wiki's entry reader (vault_import.markdown) takes: paragraphs,
headings, lists, bold and italic, a table's rows as lines. Foundry's enrichers become their label:
@UUID[…]{Fire Bolt} is "Fire Bolt", [[/r 2d6]] is "2d6", &Reference[blinded] is "blinded"."""

import re
from html.parser import HTMLParser

_LABELLED = re.compile(r"[@&]\w+\[[^\]]*\]\{([^}]*)\}", re.IGNORECASE)
_UNLABELLED = re.compile(r"&Reference\[([^\]}\s]+)[^\]}]*[\]}]|@UUID\[[^\]]*?\.([^.\]]+)\]|@Embed\[[^\]]*\]|@\w+\[[^\]]*\]", re.IGNORECASE)
_INLINE_ROLL = re.compile(r"\[\[/\w+\s+([^\]]*?)\]\](?:\{([^}]*)\})?")
# Typos the SRD packs carry are read too: "]}" for "]]", "l;ookup".
_LOOKUP = re.compile(r"\[\[l\W?ookup\s+(@[\w.]+)((?:\s+\w+)*)\][\]}](?:\{([^}]*)\})?")
_DOUBLE = re.compile(r"\[\[[^\]]*\]\]")


def _lookup(match: "re.Match[str]", names: dict[str, str]) -> str:
    """[[lookup @name lowercase]]{monster}: the owner's name where known, else the label."""
    value = names.get(match.group(1))
    if value is None:
        return match.group(3) or ""
    return value.lower() if "lowercase" in (match.group(2) or "") else value


def enrichers(text: str, names: dict[str, str] | None = None) -> str:
    """Foundry's enrichers turned to plain words; ``names`` answers lookups (@name, @item.name)."""
    text = _LOOKUP.sub(lambda match: _lookup(match, names or {}), text)
    text = _LABELLED.sub(lambda match: match.group(1), text)
    text = _INLINE_ROLL.sub(lambda match: match.group(2) or re.sub(r"\s*\w+=\S+", "", match.group(1)).strip(), text)
    text = _UNLABELLED.sub(lambda match: (match.group(1) or "").replace("-", " ") if match.group(1) else "", text)
    return _DOUBLE.sub("", text)


class _Markdown(HTMLParser):
    BLOCKS = {"p", "div", "section", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br", "hr", "dt", "dd"}

    def __init__(self, names: dict[str, str] | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.names = names
        self.lines: list[str] = []
        self.line: list[str] = []
        self.prefix = ""
        self.cells: list[str] = []
        self.in_cell = False

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self.line)).strip()
        if text:
            self.lines.append(self.prefix + text)
        self.line, self.prefix = [], ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCKS:
            self._flush()
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.prefix = "#" * max(2, min(int(tag[1]), 4)) + " "
        elif tag == "li":
            self.prefix = "- "
        elif tag in ("strong", "b"):
            self.line.append("**")
        elif tag in ("em", "i"):
            self.line.append("_")
        elif tag in ("td", "th"):
            self.in_cell, self.cells = True, self.cells
            self.line.append("" if not self.cells else "")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("strong", "b"):
            self.line.append("**")
        elif tag in ("em", "i"):
            self.line.append("_")
        elif tag in ("td", "th"):
            self.cells.append(re.sub(r"\s+", " ", "".join(self.line)).strip())
            self.line, self.in_cell = [], False
        elif tag == "tr":
            row = " — ".join(cell for cell in self.cells if cell)
            self.cells = []
            if row:
                self.lines.append(row)
        elif tag in self.BLOCKS:
            self._flush()

    def handle_data(self, data: str) -> None:
        # Again on the text itself: an enricher written as &amp;Reference[…] shows only once unescaped.
        self.line.append(enrichers(data, self.names))


def to_markdown(html: str, names: dict[str, str] | None = None) -> str:
    """``html`` (Foundry's) as Markdown paragraphs, blank-line separated; lists stay together."""
    parser = _Markdown(names)
    parser.feed(enrichers(html or "", names))
    parser.close()
    parser._flush()
    out: list[str] = []
    for line in parser.lines:
        # Empty emphasis left by enrichers that vanished.
        line = re.sub(r"\*\*\s*\*\*|(?<!\w)_\s*_(?!\w)", "", line).strip()
        if not line:
            continue
        if out and not (line.startswith("- ") and out[-1].startswith("- ")):
            out.append("")
        out.append(line)
    return "\n".join(out).strip()
