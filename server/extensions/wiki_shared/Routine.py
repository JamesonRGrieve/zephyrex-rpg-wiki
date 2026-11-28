# SPDX-License-Identifier: AGPL-3.0-or-later
"""A person's routine and motivations, and a campaign's clock (contract/routine-cases.json): the GM
side's world tick pilots people by them as in-world time advances.

- routine: an ordered schedule, each slot from and to HH:MM on days 0-6 (Monday 0) or every day
  (none), at a location, doing an activity; a slot may run overnight (from after to);
- motivations: goals, fears and current intent, a list of text;
- invariants: the lines they never cross ("never harms a child"), a list of short sentences the
  story's prompt and checks hold them to (operator, 2026-11-28);
- a clock: minutes from day 1, 00:00; a campaign without one is at clock_start_minutes (day 1, 08:00).
The lists are kept as JSON text, as a voice is.
"""

import json
import re
from typing import Any, Optional

from zephyrex.extensions.wiki_shared.Contract import CLOCK_START_MINUTES, LIMITS  # type: ignore[import-not-found]

SLOT_PARTS = ("from", "to", "days", "location_id", "activity")
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_SLOTS: int = LIMITS["routine_slots"]
MAX_ACTIVITY: int = LIMITS["activity_characters"]
MAX_MOTIVATIONS: int = LIMITS["motivations"]
MAX_MOTIVATION: int = LIMITS["motivation_characters"]
MAX_INVARIANTS: int = LIMITS["invariants"]
MAX_INVARIANT: int = LIMITS["invariant_characters"]
MINUTES_A_DAY = 24 * 60


def _loaded(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _slot(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or any(key not in SLOT_PARTS for key in value):
        raise ValueError("A slot is from, to, days, location_id and activity")
    start, end = value.get("from"), value.get("to")
    if not isinstance(start, str) or not isinstance(end, str) or not TIME.match(start) or not TIME.match(end):
        raise ValueError("A slot runs from HH:MM to HH:MM")
    days = value.get("days")
    if days is not None:
        if not isinstance(days, list) or any(isinstance(day, bool) or not isinstance(day, int) or not 0 <= day <= 6 for day in days):
            raise ValueError("A slot's days are 0 (Monday) to 6")
        days = sorted(set(days))
    location = value.get("location_id")
    if location is not None and not isinstance(location, str):
        raise ValueError("A slot's location_id is a record's id")
    activity = value.get("activity") or ""
    if not isinstance(activity, str) or len(activity) > MAX_ACTIVITY:
        raise ValueError(f"A slot's activity is text of at most {MAX_ACTIVITY} characters")
    return {"from": start, "to": end, "days": days, "location_id": location or None, "activity": activity.strip()}


def routine(value: Any) -> list[dict[str, Any]]:
    """A routine checked, its slots in order of their start."""
    value = _loaded(value)
    if not isinstance(value, list):
        raise ValueError("A routine is a list of slots")
    if len(value) > MAX_SLOTS:
        raise ValueError(f"A routine has at most {MAX_SLOTS} slots")
    return sorted((_slot(one) for one in value), key=lambda slot: (slot["from"], slot["to"]))


def _texts(value: Any, what: str, most: int, characters: int) -> list[str]:
    """A list of text trimmed, each once, blanks dropped: at most ``most`` of ``characters`` each."""
    value = _loaded(value)
    if not isinstance(value, list) or any(not isinstance(one, str) for one in value):
        raise ValueError(f"{what.capitalize()} are a list of text")
    kept = list(dict.fromkeys(one.strip() for one in value if one.strip()))
    if len(kept) > most or any(len(one) > characters for one in kept):
        raise ValueError(f"At most {most} {what} of at most {characters} characters")
    return kept


def motivations(value: Any) -> list[str]:
    """Motivations trimmed, each once, blanks dropped."""
    return _texts(value, "motivations", MAX_MOTIVATIONS, MAX_MOTIVATION)


def invariants(value: Any) -> list[str]:
    """Invariants (lines they never cross) trimmed, each once, blanks dropped."""
    return _texts(value, "invariants", MAX_INVARIANTS, MAX_INVARIANT)


def routine_text(value: Any) -> Any:
    return None if value is None else json.dumps(routine(value), ensure_ascii=False)


def motivations_text(value: Any) -> Any:
    return None if value is None else json.dumps(motivations(value), ensure_ascii=False)


def invariants_text(value: Any) -> Any:
    return None if value is None else json.dumps(invariants(value), ensure_ascii=False)


def stored_routine(text: Any) -> list[dict[str, Any]]:
    try:
        return routine(text) if text else []
    except (json.JSONDecodeError, ValueError):
        return []


def stored_motivations(text: Any) -> list[str]:
    try:
        return motivations(text) if text else []
    except (json.JSONDecodeError, ValueError):
        return []


def stored_invariants(text: Any) -> list[str]:
    try:
        return invariants(text) if text else []
    except (json.JSONDecodeError, ValueError):
        return []


def clock(minutes: Optional[int]) -> dict[str, Any]:
    """A campaign's clock: its minutes (a new one at clock_start_minutes), its day and its time."""
    held = CLOCK_START_MINUTES if minutes is None else minutes
    return {"minutes": held, "day": held // MINUTES_A_DAY + 1, "time": f"{held % MINUTES_A_DAY // 60:02d}:{held % 60:02d}"}
