# SPDX-License-Identifier: AGPL-3.0-or-later
"""The lore index's shared rules (contract/lore-index-cases.json; the client's lib/loreIndex.ts
computes the same): passages cut from a record's entry, a campaign's scope over chunks, reciprocal
rank fusion with exact name hits first, and packing to a token budget."""

import json
import math
import re
from typing import Any, Iterable, Mapping, Optional, Sequence

from zephyrex.extensions.wiki_shared.Entry import plain_text  # type: ignore[import-not-found]

RRF_K = 60
SENTENCE = re.compile(r"(?<=[.!?])\s+")
HEADING = re.compile(r"^h([1-6])$")


def tokens(text: str) -> int:
    """A text's tokens, counted as one in four characters, rounded up."""
    return math.ceil(len(text or "") / 4)


def _pieces(text: str, max_tokens: int) -> list[str]:
    """A block's text in pieces that fit: whole, else its sentences, else a long sentence's words."""
    if tokens(text) <= max_tokens:
        return [text]
    pieces: list[str] = []
    for sentence in SENTENCE.split(text):
        if tokens(sentence) <= max_tokens:
            pieces.append(sentence)
            continue
        words: list[str] = []
        for word in sentence.split():
            if words and tokens(" ".join([*words, word])) > max_tokens:
                pieces.append(" ".join(words))
                words = []
            words.append(word)
        if words:
            pieces.append(" ".join(words))
    return pieces


def chunk_entry(record: str, entry: Any, max_tokens: int = 600, min_tokens: int = 300) -> list[dict[str, Any]]:
    """A record's passages: {path: [record, heading…], text}, cut at its blocks."""
    blocks = json.loads(entry) if isinstance(entry, str) and entry else entry
    passages: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    current: list[str] = []

    def close() -> None:
        if current:
            passages.append({"path": [record, *(text for _level, text in stack)], "text": "\n".join(current)})
            current.clear()

    for block in blocks if isinstance(blocks, list) else []:
        if not isinstance(block, dict):
            continue
        heading = HEADING.match(str(block.get("type") or ""))
        text = plain_text([block]).strip()
        if heading:
            close()
            level = int(heading.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            if text:
                stack.append((level, text))
            continue
        for piece in _pieces(text, max_tokens) if text else []:
            if current and tokens("\n".join([*current, piece])) > max_tokens:
                close()
            current.append(piece)
            if tokens("\n".join(current)) >= min_tokens:
                close()
    close()
    return passages


def in_scope(campaign: Mapping[str, Any], chunk: Mapping[str, Any]) -> bool:
    """The campaign's own, its scenario's, or its setting's canon of no system or the campaign's."""
    owner = chunk.get("campaign_id")
    if owner:
        return owner in (campaign.get("id"), campaign.get("scenario_id")) and owner is not None
    if not chunk.get("setting_id") or chunk.get("setting_id") != campaign.get("setting_id"):
        return False
    system = chunk.get("game_system_id")
    return not system or system == campaign.get("game_system_id")


def fuse(rankings: Mapping[str, Sequence[str]], exact: Sequence[str] = (), k: int = RRF_K) -> list[tuple[str, float]]:
    """Exact hits first, in their order; the rest by reciprocal rank fusion, ties by id."""
    scores: dict[str, float] = {}
    for ranking in rankings.values():
        for rank, one in enumerate(ranking, start=1):
            scores[one] = scores.get(one, 0.0) + 1.0 / (k + rank)
    first = list(dict.fromkeys(exact))
    rest = sorted((one for one in scores if one not in first), key=lambda one: (-scores[one], one))
    return [(one, scores.get(one, 0.0)) for one in first + rest]


def pack(chunks: Iterable[Mapping[str, Any]], budget: int, key: str = "tokens") -> list[Mapping[str, Any]]:
    """Chunks in order while they fit the budget, skipping any that doesn't."""
    left = budget
    kept: list[Mapping[str, Any]] = []
    for one in chunks:
        size = int(one.get(key) or 0)
        if size <= left:
            kept.append(one)
            left -= size
    return kept


def prefixed(text: str, query: bool, prefix: Optional[tuple[str, str]] = ("search_document: ", "search_query: ")) -> str:
    """The text as the embedder wants it (nomic-embed-text: a task prefix on each)."""
    if prefix is None:
        return text
    return (prefix[1] if query else prefix[0]) + text
