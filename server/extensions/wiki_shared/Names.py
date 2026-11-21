# SPDX-License-Identifier: AGPL-3.0-or-later
"""S4c: a record's aliases and keywords, and a person's AI voice, checked and normalised the same way
by both back ends (the lite edition's client/src/lib/names.ts), held to
contract/name-list-cases.json. Both are kept as JSON text, as an entry is.

- aliases: other names the record goes by (mentions and link resolution use them too);
- keywords: what else wakes it in the AI's lorebook (World Info keys), beyond name and aliases;
- voice: how the AI plays a person: personality, speech, a first message and example lines.
"""

import json
from typing import Any

from zephyrex.extensions.wiki_shared.Contract import LIMITS  # type: ignore[import-not-found]

MAX_NAME = LIMITS["name_characters"]
MAX_NAMES = LIMITS["names_per_list"]
MAX_VOICE = LIMITS["voice_characters"]
MAX_EXAMPLES = LIMITS["voice_examples"]
VOICE_PARTS = ("personality", "speech", "first_message", "examples")


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


def voice(value: Any) -> dict[str, Any]:
    """A person's AI voice, every part present (empty when not given) and trimmed, each example once."""
    value = _loaded(value)
    if not isinstance(value, dict) or any(key not in VOICE_PARTS for key in value):
        raise ValueError("A voice is personality, speech, first_message and examples")
    checked: dict[str, Any] = {}
    for part in VOICE_PARTS[:3]:
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
    return checked


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
    """A stored voice read back; none when there is none or it is unreadable."""
    try:
        loaded = json.loads(text) if text else None
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None
