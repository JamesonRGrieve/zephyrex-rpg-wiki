# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading cards (JSON and PNG, V2 and V3) and World Info, and their fields as the wiki's."""

import base64
import json
import struct
import zlib
from pathlib import Path
from typing import Any

import pytest
from st_import.sillytavern import book_entries, lore_of, read_card, read_world_info, voice_of
from zephyrex.extensions.wiki_shared.Contract import LORE_CASES_PATH  # type: ignore[import-not-found]

FIXTURES = Path(__file__).parent / "fixtures"
CASES: dict[str, Any] = json.loads(LORE_CASES_PATH.read_text(encoding="utf-8"))


def png_card(*cards: tuple[str, dict[str, Any]]) -> bytes:
    """A 1×1 PNG carrying each (keyword, card) in a tEXt chunk, as SillyTavern writes one."""

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    texts = b"".join(chunk(b"tEXt", keyword.encode() + b"\x00" + base64.b64encode(json.dumps(card).encode())) for keyword, card in cards)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + texts
        + chunk(b"IDAT", zlib.compress(b"\x00\x6d\x4a\xd6"))
        + chunk(b"IEND", b"")
    )


@pytest.mark.parametrize("case", CASES["from_sillytavern"], ids=lambda case: case["name"])
def test_an_entrys_fields_as_the_wikis_lore(case: dict[str, Any]) -> None:
    assert lore_of(case["entry"]) == case["lore"]


def test_a_v2_card_its_voice_and_its_own_lorebook() -> None:
    card = read_card(FIXTURES / "holst.v2.json")
    assert (card.name, card.avatar) == ("Holst", None)
    assert voice_of(card) == {
        "personality": "Gruff but fair.",
        "speech": "",
        "first_message": "Stalls are full, User.",
        "examples": ["Holst: No credit.", "Holst: Pay first."],
        "system_prompt": "You are Holst, a stablemaster.",
        "post_history_instructions": "Stay gruff.",
        "depth_prompt": {"prompt": "Holst distrusts User.", "depth": 2, "role": "system"},
        "talkativeness": 0.3,
    }
    [stable] = book_entries(card)
    assert (stable.name, stable.keys) == ("Holst's Stable", ["stable", "stall"])
    assert lore_of(stable.fields)["position"] == "after_character"
    assert lore_of(stable.fields)["selective_logic"] == "and_all"


def test_a_png_card_prefers_v3_and_keeps_its_image(tmp_path: Path) -> None:
    path = tmp_path / "vel.png"
    path.write_bytes(png_card(("chara", {"spec": "chara_card_v2", "data": {"name": "Old Vel"}}), ("ccv3", {"spec": "chara_card_v3", "data": {"name": "Vel"}})))
    card = read_card(path)
    assert card.name == "Vel"
    assert card.avatar is not None and card.avatar.startswith(b"\x89PNG")
    plain = tmp_path / "plain.png"
    plain.write_bytes(png_card())
    with pytest.raises(ValueError, match="no character card"):
        read_card(plain)


def test_world_info_entries_named_by_comment_or_first_key() -> None:
    entries = read_world_info(FIXTURES / "waystones.world.json")
    assert [(entry.name, entry.disabled) for entry in entries] == [("The Waystones", False), ("keeper", False), ("Disabled", True)]
    assert lore_of(entries[0].fields)["group"] == "Omens"
    assert lore_of(entries[1].fields)["always_active"] is True
