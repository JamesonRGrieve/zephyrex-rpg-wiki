# SPDX-License-Identifier: AGPL-3.0-or-later
"""A hook's requirement and state (W57, from dh-campaign's tracker), the same rule as the lite
edition's (client/src/lib/requirements.ts), held to contract/requirement-cases.json.

A requirement is a hook id, ``{"all": [...]}``, ``{"any": [...]}`` or a game-system check
``{"char": {dimension: value or [values]}, "who": "any"|"all"}``, which VTT's rpg_systems
evaluates; the wiki only says a check is needed.
"""

from collections.abc import Iterable
from typing import Any, Literal, Optional

from zephyrex.extensions.wiki_shared.Contract import LIMITS  # type: ignore[import-not-found]

Value = Literal["met", "unmet", "check"]
State = Literal["resolved", "available", "blocked", "needs_check"]


class RequirementError(ValueError):
    """A requirement that isn't one of the shapes above."""


def checked(node: Any, depth: int = 0) -> Any:
    """``node`` when it's a well-formed requirement; RequirementError otherwise."""
    if depth > LIMITS["requirement_depth"]:
        raise RequirementError(f"A requirement nests at most {LIMITS['requirement_depth']} deep")
    if isinstance(node, str):
        if not node:
            raise RequirementError("A requirement names a hook")
        return node
    if not isinstance(node, dict):
        raise RequirementError("A requirement is a hook, all, any or char")
    keys = set(node) - {"who"}
    if len(keys) != 1 or not keys <= {"all", "any", "char"}:
        raise RequirementError("A requirement has exactly one of all, any or char")
    (key,) = keys
    if key in ("all", "any"):
        if "who" in node or not isinstance(node[key], list):
            raise RequirementError(f"{key} is a list of requirements")
        for child in node[key]:
            checked(child, depth + 1)
        return node
    check = node["char"]
    if not isinstance(check, dict) or not check:
        raise RequirementError("char names at least one dimension")
    for value in check.values():
        values = value if isinstance(value, list) else [value]
        if not values or not all(isinstance(item, str) and item for item in values):
            raise RequirementError("A char dimension's value is text, or a list of text")
    if node.get("who", "any") not in ("any", "all"):
        raise RequirementError("who is any or all")
    return node


def leaves(node: Any) -> list[str]:
    """The hooks a requirement names, in order, each once."""
    found: list[str] = []

    def walk(at: Any) -> None:
        if isinstance(at, str):
            if at not in found:
                found.append(at)
        elif isinstance(at, dict):
            for key in ("all", "any"):
                for child in at.get(key, []):
                    walk(child)

    walk(node)
    return found


def value(node: Any, resolved: Iterable[str]) -> Value:
    done = set(resolved)

    def of(at: Any) -> Value:
        if isinstance(at, str):
            return "met" if at in done else "unmet"
        if "char" in at:
            return "check"
        children = [of(child) for child in at.get("all", at.get("any", []))]
        if "all" in at:
            return "unmet" if "unmet" in children else "check" if "check" in children else "met"
        return "met" if "met" in children else "check" if "check" in children else "unmet"

    return of(node)


def hook_state(requires: Optional[Any], resolved: Iterable[str], self_resolved: bool) -> State:
    """Resolved; else available, needs_check or blocked, from the requirement (none: available)."""
    if self_resolved:
        return "resolved"
    if requires is None:
        return "available"
    return {"met": "available", "check": "needs_check", "unmet": "blocked"}[value(requires, resolved)]
