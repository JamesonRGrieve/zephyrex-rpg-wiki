# SPDX-License-Identifier: AGPL-3.0-or-later
"""A record's summary for a lorebook entry (rpg-ai A15), the same rule as the lite edition's
(client/src/lib/summary.ts) and rpg-ai's, held to contract/summary-cases.json: whitespace runs become
one space; within the limit the text stands; longer, it is cut at the last space leaving room for
"…" (or at the limit less one when there is none), trimmed, and "…" added."""

import re

from zephyrex.extensions.wiki_shared.Contract import LIMITS  # type: ignore[import-not-found]

SUMMARY_CHARACTERS: int = LIMITS["summary_characters"]
ELLIPSIS = "…"


def summary(text: str | None, limit: int = SUMMARY_CHARACTERS) -> str:
    """The summary of a plain text, at most ``limit`` characters."""
    flat = re.sub(r"\s+", " ", text or "").strip()
    if len(flat) <= limit:
        return flat
    room = flat[: limit - 1]
    cut = room.rfind(" ")
    return (room[:cut] if cut > 0 else room).rstrip() + ELLIPSIS
