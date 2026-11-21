# SPDX-License-Identifier: AGPL-3.0-or-later
"""S4d: a record's lorebook activation, the fields of SillyTavern's World Info that rpg-ai's
activation reads (its keys are the record's name, aliases and keywords). Checked and filled with
the contract's defaults the same way by both back ends (the client package's lib/lore.ts), held to
contract/lore-cases.json, and kept as JSON text, as an entry is.

- always_active (ST constant), order (insertion order), position and depth (where it goes in the
  prompt), probability (0-100);
- selective_logic over secondary_keys (ST's AND ANY / NOT ALL / NOT ANY / AND ALL);
- sticky, cooldown and delay (in messages); group and group_weight (an inclusion group).
"""

import json
from typing import Any

from zephyrex.extensions.wiki_shared.Contract import LORE_DEFAULTS, LORE_LOGIC, LORE_POSITIONS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Names import names  # type: ignore[import-not-found]

MAX_GROUP = 200
WHOLE_FIELDS = ("order", "depth", "probability", "sticky", "cooldown", "delay", "group_weight")


def _whole(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} is a whole number")
    if name == "probability" and not 0 <= value <= 100:
        raise ValueError("probability is a whole number from 0 to 100")
    if name in ("depth", "sticky", "cooldown", "delay") and value < 0:
        raise ValueError(f"{name} is a whole number of zero or more")
    if name == "group_weight" and value < 1:
        raise ValueError("group_weight is a whole number of one or more")
    return value


def lore(value: Any) -> dict[str, Any]:
    """A lore block, every field present (the contract's default when not given)."""
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict) or any(key not in LORE_DEFAULTS for key in value):
        raise ValueError("A lore block is an object of SillyTavern's activation fields")
    checked = {**LORE_DEFAULTS, **value}
    if not isinstance(checked["always_active"], bool):
        raise ValueError("always_active is true or false")
    if checked["position"] not in LORE_POSITIONS:
        raise ValueError(f"A lore position is one of: {', '.join(LORE_POSITIONS)}")
    if checked["selective_logic"] not in LORE_LOGIC:
        raise ValueError(f"Lore logic is one of: {', '.join(LORE_LOGIC)}")
    for name in WHOLE_FIELDS:
        checked[name] = _whole(name, checked[name])
    checked["secondary_keys"] = names(checked["secondary_keys"])
    group = checked["group"]
    if not isinstance(group, str) or len(group.strip()) > MAX_GROUP:
        raise ValueError(f"A lore group is a name of at most {MAX_GROUP} characters")
    checked["group"] = group.strip()
    return checked


def lore_text(value: Any) -> Any:
    """A lore block as it is stored: JSON text, or none."""
    return None if value is None else json.dumps(lore(value), ensure_ascii=False)


def stored_lore(text: Any) -> Any:
    """A stored lore block read back; none when there is none or it is unreadable."""
    try:
        loaded = json.loads(text) if text else None
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None
