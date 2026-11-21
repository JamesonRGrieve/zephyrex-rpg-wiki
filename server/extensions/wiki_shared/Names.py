# SPDX-License-Identifier: AGPL-3.0-or-later
"""S4c: a record's aliases and keywords, and a person's AI voice, checked and normalised the same way
by both back ends (the lite edition's client/src/lib/names.ts), held to
contract/name-list-cases.json. Both are kept as JSON text, as an entry is.

- aliases: other names the record goes by (mentions and link resolution use them too);
- keywords: what else wakes it in the AI's lorebook (World Info keys), beyond name and aliases;
- voice: how the AI plays a person: personality, speech, a first message and example lines, and
  (Parity, SillyTavern's card fields) a system prompt, post-history instructions, a depth prompt
  (Character's Note: a prompt, a depth and a role), talkativeness (0 to 1) and across_chats.
"""

import json
from typing import Any

from zephyrex.extensions.wiki_shared.Contract import CONTRACT, LIMITS  # type: ignore[import-not-found]

MAX_NAME = LIMITS["name_characters"]
MAX_NAMES = LIMITS["names_per_list"]
MAX_VOICE = LIMITS["voice_characters"]
MAX_EXAMPLES = LIMITS["voice_examples"]
VOICE_PARTS: tuple[str, ...] = tuple(CONTRACT["voice_parts"])
VOICE_DEFAULTS: dict[str, Any] = CONTRACT["voice_defaults"]
DEPTH_ROLES: tuple[str, ...] = tuple(CONTRACT["depth_prompt_roles"])
MAX_DEPTH = LIMITS["depth_prompt_depth"]
TEXT_PARTS = ("personality", "speech", "first_message", "system_prompt", "post_history_instructions")
PARTS_RULE = f"A voice's parts are {', '.join(VOICE_PARTS)}"
DEPTH_RULE = f"A voice's depth_prompt is a prompt, a depth from 0 to {MAX_DEPTH} and a role ({', '.join(DEPTH_ROLES)})"


def _loaded(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def names(value: Any) -> list[str]:
    """A list of names: each trimmed, blanks dropped, each once (case aside), in order."""
    value = _loaded(value)
    if not isinstance(value, list) or any(not isinstance(one, str) for one in value):
        raise ValueError("A list of names is a list of text")
    seen: set[str] = set()
    kept: list[str] = []
    for one in value:
        name = one.strip()
        if not name or name.casefold() in seen:
            continue
        if len(name) > MAX_NAME:
            raise ValueError(f"A name has at most {MAX_NAME} characters")
        seen.add(name.casefold())
        kept.append(name)
    if len(kept) > MAX_NAMES:
        raise ValueError(f"A list holds at most {MAX_NAMES} names")
    return kept


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _depth_prompt(value: Any) -> Any:
    """A Character's Note: none, or its prompt (none when empty), depth and role."""
    if value is None:
        return None
    if not isinstance(value, dict) or any(key not in ("prompt", "depth", "role") for key in value):
        raise ValueError(DEPTH_RULE)
    prompt = value.get("prompt") or ""
    depth = value.get("depth", VOICE_DEFAULTS["depth_prompt_depth"])
    role = value.get("role") or VOICE_DEFAULTS["depth_prompt_role"]
    if not isinstance(prompt, str) or len(prompt) > MAX_VOICE or not isinstance(depth, int) or isinstance(depth, bool):
        raise ValueError(DEPTH_RULE)
    if not 0 <= depth <= MAX_DEPTH or role not in DEPTH_ROLES:
        raise ValueError(DEPTH_RULE)
    return {"prompt": prompt.strip(), "depth": depth, "role": role} if prompt.strip() else None


def voice(value: Any) -> dict[str, Any]:
    """A person's AI voice, every part present (empty or its default when not given) and trimmed,
    each example once."""
    value = _loaded(value)
    if not isinstance(value, dict) or any(key not in VOICE_PARTS for key in value):
        raise ValueError(PARTS_RULE)
    checked: dict[str, Any] = {}
    for part in TEXT_PARTS:
        text = value.get(part) or ""
        if not isinstance(text, str):
            raise ValueError(f"A voice's {part} is text")
        if len(text) > MAX_VOICE:
            raise ValueError(f"A voice's {part} has at most {MAX_VOICE} characters")
        checked[part] = text.strip()
    examples = value.get("examples") or []
    if not isinstance(examples, list) or any(not isinstance(one, str) for one in examples):
        raise ValueError("A voice's examples are a list of text")
    kept = list(dict.fromkeys(one.strip() for one in examples if one.strip()))
    if len(kept) > MAX_EXAMPLES or any(len(one) > MAX_VOICE for one in kept):
        raise ValueError(f"A voice has at most {MAX_EXAMPLES} examples of at most {MAX_VOICE} characters")
    checked["examples"] = kept
    checked["depth_prompt"] = _depth_prompt(value.get("depth_prompt"))
    talkativeness = value.get("talkativeness", VOICE_DEFAULTS["talkativeness"])
    if not _number(talkativeness) or not 0 <= talkativeness <= 1:
        raise ValueError("A voice's talkativeness is from 0 to 1")
    checked["talkativeness"] = talkativeness
    across = value.get("across_chats", VOICE_DEFAULTS["across_chats"])
    if not isinstance(across, bool):
        raise ValueError("A voice's across_chats is yes or no")
    checked["across_chats"] = across
    return {part: checked[part] for part in VOICE_PARTS}


def names_text(value: Any) -> Any:
    """A list of names as it is stored: JSON text, or none."""
    return None if value is None else json.dumps(names(value), ensure_ascii=False)


def voice_text(value: Any) -> Any:
    """A voice as it is stored: JSON text, or none."""
    return None if value is None else json.dumps(voice(value), ensure_ascii=False)


def stored_names(text: Any) -> list[str]:
    """A stored list read back; an unreadable one is empty."""
    try:
        loaded = json.loads(text) if text else []
    except json.JSONDecodeError:
        return []
    return [one for one in loaded if isinstance(one, str)] if isinstance(loaded, list) else []


def stored_voice(text: Any) -> Any:
    """A stored voice read back with every part (one stored before a part existed gets its default);
    none when there is none or it is unreadable."""
    try:
        return voice(text) if text else None
    except (json.JSONDecodeError, ValueError):
        return None
