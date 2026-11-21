# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading SillyTavern's files: character cards (V1, V2 and V3, as JSON or embedded in a PNG's text
chunks, V3's preferred) and World Info (a lorebook's JSON, or a card's character_book), and their
activation fields as the wiki's lore block (contract/lore-cases.json from_sillytavern)."""

import base64
import json
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from zephyrex.extensions.wiki_shared.Contract import LORE_DEFAULTS, LORE_LOGIC, LORE_POSITIONS  # type: ignore[import-not-found]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# A character_book entry's position, before extensions.position named it as a number.
BOOK_POSITIONS = {"before_char": 0, "after_char": 1}


@dataclass
class Card:
    path: str
    data: dict[str, Any]
    avatar: Optional[bytes] = None

    @property
    def name(self) -> str:
        return str(self.data.get("name") or Path(self.path).stem).strip()


@dataclass
class Entry:
    """One World Info entry, in SillyTavern's own field names."""

    source: str
    fields: dict[str, Any] = field(default_factory=dict)

    @property
    def keys(self) -> list[str]:
        return [str(one) for one in self.fields.get("key") or [] if str(one).strip()]

    @property
    def name(self) -> str:
        comment = str(self.fields.get("comment") or "").strip()
        return comment or (self.keys[0] if self.keys else f"Entry {self.fields.get('uid', '')}".strip())

    @property
    def disabled(self) -> bool:
        return bool(self.fields.get("disable"))


def _png_texts(content: bytes) -> dict[str, str]:
    """A PNG's tEXt and iTXt chunks, keyword → text."""
    if not content.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG")
    texts: dict[str, str] = {}
    at = len(PNG_SIGNATURE)
    while at + 8 <= len(content):
        (length,) = struct.unpack(">I", content[at : at + 4])
        kind = content[at + 4 : at + 8]
        body = content[at + 8 : at + 8 + length]
        at += 12 + length
        if kind == b"tEXt":
            keyword, _, text = body.partition(b"\x00")
            texts[keyword.decode("latin-1")] = text.decode("latin-1")
        elif kind == b"iTXt":
            keyword, _, rest = body.partition(b"\x00")
            compressed, rest = rest[0], rest[2:]
            _language, _, rest = rest.partition(b"\x00")
            _translated, _, text = rest.partition(b"\x00")
            texts[keyword.decode("latin-1")] = (zlib.decompress(text) if compressed else text).decode("utf-8")
        elif kind == b"IEND":
            break
    return texts


def _card_data(raw: dict[str, Any]) -> dict[str, Any]:
    """A card's fields: V2/V3 keep them under data; V1 has them at the top."""
    data = raw.get("data")
    return data if isinstance(data, dict) and str(raw.get("spec", "")).startswith("chara_card_v") else raw


def read_card(path: Path) -> Card:
    content = path.read_bytes()
    if content.startswith(PNG_SIGNATURE):
        texts = _png_texts(content)
        chunk = texts.get("ccv3") or texts.get("chara")
        if chunk is None:
            raise ValueError("the PNG carries no character card (no ccv3 or chara chunk)")
        return Card(str(path), _card_data(json.loads(base64.b64decode(chunk))), avatar=content)
    return Card(str(path), _card_data(json.loads(content.decode("utf-8"))))


def _book_entry(source: str, raw: dict[str, Any]) -> Entry:
    """A character_book entry in World Info's field names."""
    extensions = raw.get("extensions") or {}
    position = extensions.get("position", BOOK_POSITIONS.get(str(raw.get("position") or ""), 0))
    return Entry(
        source,
        {
            "uid": raw.get("id"),
            "key": raw.get("keys") or [],
            "keysecondary": raw.get("secondary_keys") or [],
            "comment": raw.get("comment") or raw.get("name") or "",
            "content": raw.get("content") or "",
            "disable": raw.get("enabled") is False,
            "constant": bool(raw.get("constant")),
            "selective": raw.get("selective", True),
            "order": raw.get("insertion_order", LORE_DEFAULTS["order"]),
            "position": position,
            "depth": extensions.get("depth"),
            "probability": extensions.get("probability"),
            "useProbability": extensions.get("useProbability", True),
            "selectiveLogic": extensions.get("selectiveLogic"),
            "sticky": extensions.get("sticky"),
            "cooldown": extensions.get("cooldown"),
            "delay": extensions.get("delay"),
            "group": extensions.get("group"),
            "groupWeight": extensions.get("group_weight"),
        },
    )


def read_world_info(path: Path) -> list[Entry]:
    """A World Info file's entries ({entries: {uid: {...}}}), or a character_book's."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries", {})
    if isinstance(entries, dict):
        return [Entry(f"{path}#{uid}", {"uid": uid, **entry}) for uid, entry in entries.items()]
    return [_book_entry(f"{path}#{index}", entry) for index, entry in enumerate(entries)]


def book_entries(card: Card) -> list[Entry]:
    """A card's own lorebook (character_book), as World Info entries."""
    book = card.data.get("character_book") or {}
    return [_book_entry(f"{card.path}#book{index}", entry) for index, entry in enumerate(book.get("entries") or [])]


def _number(value: Any, default: int) -> int:
    return default if value is None or isinstance(value, bool) else int(value)


def lore_of(fields: dict[str, Any]) -> dict[str, Any]:
    """An entry's activation fields as the wiki's lore block (positions and logic named)."""
    position = _number(fields.get("position"), 0)
    logic = _number(fields.get("selectiveLogic"), 0)
    selective = fields.get("selective", True) is not False
    uses_probability = fields.get("useProbability", True) is not False
    return {
        "always_active": bool(fields.get("constant")),
        "order": _number(fields.get("order"), LORE_DEFAULTS["order"]),
        "position": LORE_POSITIONS[position] if 0 <= position < len(LORE_POSITIONS) else LORE_DEFAULTS["position"],
        "depth": _number(fields.get("depth"), LORE_DEFAULTS["depth"]),
        "probability": _number(fields.get("probability"), 100) if uses_probability else 100,
        "selective_logic": LORE_LOGIC[logic] if 0 <= logic < len(LORE_LOGIC) else LORE_DEFAULTS["selective_logic"],
        "secondary_keys": [str(one) for one in fields.get("keysecondary") or [] if str(one).strip()] if selective else [],
        "sticky": _number(fields.get("sticky"), 0),
        "cooldown": _number(fields.get("cooldown"), 0),
        "delay": _number(fields.get("delay"), 0),
        "group": str(fields.get("group") or "").strip(),
        "group_weight": _number(fields.get("groupWeight"), LORE_DEFAULTS["group_weight"]),
    }


def voice_of(card: Card) -> dict[str, Any]:
    """A card's personality, first message and example lines (split at <START>), {{char}} and
    {{user}} read as the character's name and "User"."""
    name = card.name

    def filled(text: Any) -> str:
        return str(text or "").replace("{{char}}", name).replace("{{user}}", "User").replace("<USER>", "User").replace("<BOT>", name).strip()

    examples = [filled(one) for one in str(card.data.get("mes_example") or "").split("<START>")]
    return {
        "personality": filled(card.data.get("personality")),
        "speech": "",
        "first_message": filled(card.data.get("first_mes")),
        "examples": list(dict.fromkeys(one for one in examples if one)),
    }
