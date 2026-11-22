# SPDX-License-Identifier: AGPL-3.0-or-later
"""The world's activation index (contract/world-keys-cases.json; the client's lib/worldKeys.ts
computes the same): a record's keys, and the keys a text holds, so a narrator's turn reads only the
records its text names (world_entities_matching), never a whole setting."""

import re
import unicodedata
from typing import Iterable

ALWAYS = "*"
MAX_WORDS = 8
NON_WORD = re.compile(r"[^0-9a-z]+")


def normalised(text: str) -> str:
    """Accents dropped, case folded, anything not a letter or digit one space."""
    flat = "".join(char for char in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(char))
    return NON_WORD.sub(" ", flat.casefold()).strip()


def record_keys(name: str, aliases: Iterable[str], keywords: Iterable[str], always_active: bool) -> list[str]:
    """A record's keys: its name, aliases and keywords normalised, 1 to 8 words of 2+ characters,
    regular expressions (/…/) left out; "*" too when it is always active."""
    keys: set[str] = {ALWAYS} if always_active else set()
    for raw in [name, *aliases, *keywords]:
        text = str(raw or "").strip()
        if len(text) > 1 and text.startswith("/") and text.endswith("/"):
            continue
        key = normalised(text)
        if len(key) >= 2 and len(key.split()) <= MAX_WORDS:
            keys.add(key)
    return sorted(keys)


def text_grams(text: str) -> set[str]:
    """Every run of 1 to 8 words of the normalised text."""
    words = normalised(text).split()
    return {" ".join(words[start : start + size]) for start in range(len(words)) for size in range(1, MAX_WORDS + 1) if start + size <= len(words)}
