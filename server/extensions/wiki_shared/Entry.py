# SPDX-License-Identifier: AGPL-3.0-or-later
"""A record's entry: a Plate (Slate) value, stored as JSON text, with a plain-text copy kept as the
record's description for search (decision 16; operator, 2026-11-20). The rule is shared with the
lite edition (client/src/lib/entry.ts) and held to contract/entry-text-cases.json on both sides:
an element with a text leaf among its children is one line (inline elements in it give their
text); any other element is a container whose children are read in turn."""

import json
from typing import Any

from zephyrex.extensions.wiki_shared.Contract import LIMITS  # type: ignore[import-not-found]

MAX_BYTES: int = LIMITS["entry_bytes"]
MAX_DEPTH: int = LIMITS["entry_depth"]


def _is_leaf(node: Any) -> bool:
    return isinstance(node, dict) and "text" in node and "children" not in node


def _check(node: Any, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise ValueError(f"An entry nests at most {MAX_DEPTH} levels")
    if _is_leaf(node):
        if not isinstance(node["text"], str):
            raise ValueError("A text leaf's text must be a string")
        return
    if not isinstance(node, dict) or not isinstance(node.get("children"), list):
        raise ValueError("Every node in an entry is an element with children or a text leaf")
    for child in node["children"]:
        _check(child, depth + 1)


def checked(value: Any) -> list[Any]:
    """The entry as a list of nodes, or a ValueError saying what is wrong with it."""
    if not isinstance(value, list):
        raise ValueError("An entry is a list of block elements")
    for node in value:
        _check(node, 1)
    return value


def _text_of(node: dict[str, Any]) -> str:
    if _is_leaf(node):
        return str(node["text"])
    return "".join(_text_of(child) for child in node["children"])


def _lines(nodes: list[Any]) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        if _is_leaf(node):
            continue
        if any(_is_leaf(child) for child in node["children"]):
            lines.append(_text_of(node))
        else:
            lines.extend(_lines(node["children"]))
    return lines


def plain_text(entry: list[Any]) -> str:
    """The entry's plain-text copy: each line's text, joined by newlines."""
    return "\n".join(_lines(checked(entry)))


def parse(raw: Any) -> tuple[str, str]:
    """An entry as sent (its JSON text, or the value itself) → (stored JSON text, plain text)."""
    value = json.loads(raw) if isinstance(raw, str) else raw
    text = json.dumps(checked(value), ensure_ascii=False, separators=(",", ":"))
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError(f"An entry holds at most {MAX_BYTES} bytes")
    return text, plain_text(value)
