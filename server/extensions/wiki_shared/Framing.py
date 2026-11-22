# SPDX-License-Identifier: AGPL-3.0-or-later
"""A campaign's framing entry split into its public text and its GM part (contract/framing-cases.json;
the client's lib/framing.ts computes the same)."""

import json
import re
from typing import Any

from zephyrex.extensions.wiki_shared.Entry import plain_text  # type: ignore[import-not-found]

GM_HEADING = re.compile(r"\b(gm|game ?master|secrets?|behind the scenes)\b", re.IGNORECASE)
HEADINGS = {"h2", "h3", "h4", "h5", "h6"}


def framing_parts(entry: Any) -> tuple[str, str]:
    """(public, gm): the title (h1) left out; each h2-h6 heading opens a section, the GM's when its
    heading names the GM, a game master, secrets or what's behind the scenes."""
    blocks = json.loads(entry) if isinstance(entry, str) and entry else entry
    if not isinstance(blocks, list):
        return "", ""
    public: list[list[str]] = [[]]
    gm: list[list[str]] = []
    into = public[0]
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        text = plain_text([block]).strip()
        if kind == "h1":
            continue
        if kind in HEADINGS:
            into = [text] if text else []
            (gm if GM_HEADING.search(text) else public).append(into)
            continue
        if text:
            into.append(text)
    joined = lambda sections: "\n\n".join("\n".join(lines) for lines in sections if lines)  # noqa: E731
    return joined(public), joined(gm)
