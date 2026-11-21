# SPDX-License-Identifier: AGPL-3.0-or-later
"""Whom a person regards how, now (W56, from dh-campaign's tracker), the same rule as the lite
edition's (client/src/lib/dispositions.ts), held to contract/disposition-cases.json.

Toward one target, a person has one default entry and any number with a trigger hook. The
current attitude is the entry whose trigger was resolved most recently (a later entry wins a
tie), else the default, else none. A nuance attitude reads as its band (contract
``attitude_nuances``) wherever only the scale is understood.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from zephyrex.extensions.wiki_shared.Contract import ATTITUDE_NUANCES, ATTITUDES  # type: ignore[import-not-found]


def checked_attitude(value: Any) -> Any:
    """An attitude from the scale or a nuance of it, or none."""
    if value is not None and value not in ATTITUDES and value not in ATTITUDE_NUANCES:
        raise ValueError(f"An attitude is one of: {', '.join(ATTITUDES)}, or a nuance of one")
    return value


def band(attitude: str) -> str:
    """The scale's attitude a nuance reads as; a scale attitude reads as itself."""
    return ATTITUDE_NUANCES.get(attitude, attitude)


def current(entries: Sequence[Mapping[str, Any]], resolved: Mapping[str, Any]) -> Optional[str]:
    """The current attitude from ``entries`` (attitude, default, trigger) and when each resolved
    hook was resolved (any comparable stamp)."""
    best: Optional[tuple[Any, int]] = None
    chosen: Optional[str] = None
    for index, entry in enumerate(entries):
        trigger = entry.get("trigger")
        if trigger and trigger in resolved:
            rank = (resolved[trigger], index)
            if best is None or rank >= best:
                best, chosen = rank, entry["attitude"]
    if chosen is not None:
        return chosen
    defaults = [entry["attitude"] for entry in entries if entry.get("default")]
    return defaults[-1] if defaults else None
