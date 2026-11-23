# SPDX-License-Identifier: AGPL-3.0-or-later
"""A SillyTavern character card as a wiki person (contract/card-cases.json; the client's
lib/cards.ts computes the same): st_import's import and rpg_core's import_card_person share it.

A card's fields are the spec's (description, personality, scenario, first_mes, mes_example,
alternate_greetings, tags, system_prompt, post_history_instructions, extensions) or rpg-ai's names
for the same (first_message, example_messages)."""

from typing import Any, Optional

ALIASES = {"first_message": "first_mes", "example_messages": "mes_example"}
CHARACTERS = "Characters"  # the requester's campaign for characters outside any scenario


def card_data(card: dict[str, Any]) -> dict[str, Any]:
    """The card's fields under the spec's names."""
    data = dict(card)
    for alias, name in ALIASES.items():
        if name not in data and alias in data:
            data[name] = data[alias]
    return data


def _talkativeness(value: Any) -> Any:
    """A card's talkativeness (SillyTavern writes it as text or a number); unreadable reads as none."""
    try:
        return None if value is None or value == "" or isinstance(value, bool) else float(value)
    except (TypeError, ValueError):
        return None


def card_voice(name: str, data: dict[str, Any]) -> dict[str, Any]:
    """A card's personality, first message and example lines (split at <START>), its system prompt,
    post-history instructions, Character's Note (extensions.depth_prompt) and talkativeness;
    {{char}} and {{user}} read as the character's name and "User"."""

    def filled(text: Any) -> str:
        return str(text or "").replace("{{char}}", name).replace("{{user}}", "User").replace("<USER>", "User").replace("<BOT>", name).strip()

    examples = [filled(one) for one in str(data.get("mes_example") or "").split("<START>")]
    extensions = data.get("extensions") or {}
    note = extensions.get("depth_prompt") or {}
    given: dict[str, Any] = {
        "personality": filled(data.get("personality")),
        "speech": "",
        "first_message": filled(data.get("first_mes")),
        "examples": list(dict.fromkeys(one for one in examples if one)),
        "system_prompt": filled(data.get("system_prompt")),
        "post_history_instructions": filled(data.get("post_history_instructions")),
    }
    if isinstance(note, dict) and str(note.get("prompt") or "").strip():
        given["depth_prompt"] = {"prompt": filled(note.get("prompt")), "depth": int(note.get("depth", 4)), "role": str(note.get("role") or "system")}
    talkativeness = _talkativeness(extensions.get("talkativeness"))
    if talkativeness is not None:
        given["talkativeness"] = talkativeness
    return given


def card_markdown(data: dict[str, Any]) -> str:
    """The person's entry, as Markdown: the description, then the scenario under its own heading."""
    description = str(data.get("description") or "").strip()
    scenario = str(data.get("scenario") or "").strip()
    return description + (f"\n\n## Scenario\n\n{scenario}" if scenario else "")


def card_greetings(data: dict[str, Any]) -> list[str]:
    return [str(one).strip() for one in data.get("alternate_greetings") or [] if str(one).strip()]


def card_tags(data: dict[str, Any]) -> list[str]:
    return list(dict.fromkeys(str(one).strip() for one in data.get("tags") or [] if str(one).strip()))


def card_avatar(card: dict[str, Any]) -> Optional[str]:
    """The card's picture as given: an https link or an uploaded asset's id; a data URL is refused
    (upload it first, POST /v1/asset/upload), as fill_person refuses one."""
    avatar = str(card.get("avatar") or "").strip()
    if avatar.startswith("data:"):
        raise ValueError("Upload the avatar first (POST /v1/asset/upload) and give its asset id or an https link")
    return avatar or None
