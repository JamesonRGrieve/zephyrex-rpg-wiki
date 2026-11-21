# SPDX-License-Identifier: AGPL-3.0-or-later
"""The checks every wiki record takes, the same as the lite edition's (client/src/lib/worldRecords.ts):
a trimmed name within the contract's length, a kind from the contract's list, an entry stored with
its plain text as the description, and a parent that never closes a cycle (422, as lite answers)."""

import re
from typing import Any, Callable, Optional

from fastapi import HTTPException
from zephyrex.extensions.wiki_shared.Contract import (  # type: ignore[import-not-found]
    LIMITS,
    SETTING_SLUG_CHARACTERS,
    SETTING_SLUG_PATTERN,
)
from zephyrex.extensions.wiki_shared.Entry import parse as parse_entry  # type: ignore[import-not-found]
from zephyrex.lib.CycleGuard import CycleGuardError, would_create_tree_cycle
from zephyrex.logic.AbstractLogicManager import AbstractBLLManager, HookContext

MAX_NAME: int = LIMITS["name_characters"]


def checked_name(value: Any) -> Any:
    """A name, trimmed: required, and at most the contract's length."""
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        raise ValueError("A name is required")
    if len(stripped) > MAX_NAME:
        raise ValueError(f"A name has at most {MAX_NAME} characters")
    return stripped


def checked_kind(value: Any, kinds: tuple[str, ...], what: str) -> Any:
    """A kind from the contract's list for ``what``, or None."""
    if value is None or value in kinds:
        return value
    raise ValueError(f"A {what}'s kind is one of: {', '.join(kinds)}")


def checked_quantity(value: Any) -> Any:
    """A count of one or more."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("A quantity is a whole number of one or more")
    return value


def with_entry_text(payload: Any) -> Any:
    """Store the entry as compact JSON text and its plain-text copy as the description."""
    entry = getattr(payload, "entry", None)
    if entry is not None:
        stored, text = parse_entry(entry)
        payload.entry = stored
        payload.description = text
    return payload


def _parent_of(manager: AbstractBLLManager) -> Callable[[str], Optional[str]]:
    def _get(record_id: str) -> Optional[str]:
        try:
            row = manager.get(id=record_id)
        except Exception:
            return None
        return getattr(row, "parent_id", None) if row else None

    return _get


def refuse_parent_cycle(context: HookContext, what: str) -> None:
    """For a BEFORE hook on a tree's manager: a record can't sit under itself or its descendants."""
    if context.method_name != "update":
        return
    candidate = context.kwarg("parent_id", default=None)
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if not candidate or not record_id:
        return
    try:
        cycle = would_create_tree_cycle(record_id, candidate, _parent_of(context.manager))
    except CycleGuardError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if cycle:
        raise HTTPException(status_code=422, detail=f"A {what} can't sit under itself or its own descendants")


COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def checked_colour(value: Any) -> Any:
    """A colour is #rrggbb (the lite edition's rule too), or none."""
    if value is not None and not COLOUR.match(value):
        raise ValueError("A colour is # and six hex digits, like #a83232")
    return value


SETTING_SLUG = re.compile(SETTING_SLUG_PATTERN)


def slugify(name: str) -> str:
    """A setting's slug from its name (contract/slug-cases.json): lower case, every other run of
    characters one hyphen, at most the contract's length; "unnamed" when nothing is left."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:SETTING_SLUG_CHARACTERS].strip("-") or "unnamed"


def free_slug(slug: str, taken: set[str]) -> str:
    """``slug``, or with the first -2, -3… not in ``taken``, still within the contract's length."""
    if slug not in taken:
        return slug
    number = 2
    while True:
        suffix = f"-{number}"
        candidate = f"{slug[: SETTING_SLUG_CHARACTERS - len(suffix)].rstrip('-')}{suffix}"
        if candidate not in taken:
            return candidate
        number += 1


def checked_slug(value: Any) -> Any:
    """A slug the contract allows, or none (then it is derived from the name)."""
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > SETTING_SLUG_CHARACTERS or not SETTING_SLUG.match(value):
        raise ValueError(
            f"A slug is lower-case letters and digits in words joined by single hyphens, at most {SETTING_SLUG_CHARACTERS} characters"
        )
    return value
