# SPDX-License-Identifier: AGPL-3.0-or-later
"""A session report's body as a Plate value (rpg-ai A24), the same rule as the lite edition's
(client/src/lib/report.ts), held to contract/report-body-cases.json. The title is the journal's name
and never appears in the body. Plain text becomes one paragraph per blank-line-separated block;
mentions close the body with a "Mentioned:" paragraph of mention nodes (typed references, never
names alone: DESIGN's @ rule)."""

import re
from typing import Any

from zephyrex.extensions.wiki_shared.Entry import checked  # type: ignore[import-not-found]


def _paragraphs(text: str) -> list[dict[str, Any]]:
    blocks = (block.strip() for block in re.split(r"\n\s*\n", text))
    return [{"type": "p", "children": [{"text": block}]} for block in blocks if block]


def report_entry(body: str | list[Any], mentions: list[dict[str, str]]) -> list[Any]:
    """The report's entry: its body's paragraphs (or its Plate value), then its mentions.

    Each mention is {target_entity_type, target_entity_id, name}; the caller has checked it."""
    entry: list[Any] = list(checked(body)) if isinstance(body, list) else _paragraphs(body)
    if mentions:
        children: list[dict[str, Any]] = [{"text": "Mentioned: "}]
        for index, mention in enumerate(mentions):
            if index > 0:
                children.append({"text": ", "})
            children.append(
                {
                    "type": "mention",
                    "target_entity_type": mention["target_entity_type"],
                    "target_entity_id": mention["target_entity_id"],
                    "children": [{"text": mention["name"]}],
                }
            )
        children.append({"text": ""})
        entry.append({"type": "p", "children": children})
    return entry
