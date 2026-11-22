# SPDX-License-Identifier: AGPL-3.0-or-later
"""The rules a playable scenario keeps, and how a broken one is mended (pure: no API).

Sullenmire's breakage (prod, 2026-11-22): its people had no kind (so no cast, no party), its framing's
Opening Situation was only a pointer to other notes ("See [[…]]; the event graph is [[…]], and
play-by-play is in [[…]]"), and nothing said where play starts."""

import json
import re
from typing import Any, Iterable, Optional

from zephyrex.extensions.wiki_shared.Entry import plain_text  # type: ignore[import-not-found]

try:
    from zephyrex.extensions.wiki_shared.WorldKeys import record_keys, text_grams  # type: ignore[import-not-found]
except ImportError:
    # An installed wiki older than b2effb7 (prod's cd32e9e) has no WorldKeys: the same file is loaded
    # from beside this package (server/extensions/wiki_shared/WorldKeys.py; it needs only the
    # standard library), so the repair runs in process on that build.
    import importlib.util
    from pathlib import Path

    _spec = importlib.util.spec_from_file_location("scenario_repair_world_keys", Path(__file__).resolve().parents[1] / "extensions" / "wiki_shared" / "WorldKeys.py")
    if _spec is None or _spec.loader is None:
        raise
    _world_keys = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_world_keys)
    record_keys, text_grams = _world_keys.record_keys, _world_keys.text_grams

OPENING = re.compile(r"^opening\b", re.IGNORECASE)
START = re.compile(r"^start(ing)?\s+(location|place)\b", re.IGNORECASE)
OVERVIEW = re.compile(r"^(overview|about|how to use)\b", re.IGNORECASE)
POINTER_WORDS = re.compile(r"\b(event graph|play-by-play|run \d+ record|run record|run sheet)\b", re.IGNORECASE)
HEADING = re.compile(r"^h([1-6])$")
BRIEFING = re.compile(r"player briefing", re.IGNORECASE)
# A framing note by its name, as rpg-ai's isFraming reads it ("Sullenmire: Campaign Framing"), or the
# fixture vault's "The Split Antler — Framing": framings imported before campaign_framing was a
# journal kind (2026-11-21) came in as lore.
FRAMING_NAME = re.compile(r"(:\s*campaign framing|\s[—–-]\s*(campaign\s+)?framing)\s*$", re.IGNORECASE)
MIN_TELLING = 40
SOURCES = "Sources:"


def blocks_of(entry: Any) -> list[dict[str, Any]]:
    blocks = json.loads(entry) if isinstance(entry, str) and entry else entry
    return [block for block in blocks if isinstance(block, dict)] if isinstance(blocks, list) else []


def sections(blocks: list[dict[str, Any]]) -> list[tuple[str, int, int, int]]:
    """Each heading's section: (heading text, level, its index, the index its section ends at)."""
    found: list[tuple[str, int, int]] = []
    for index, block in enumerate(blocks):
        heading = HEADING.match(str(block.get("type") or ""))
        if heading:
            found.append((plain_text([block]).strip(), int(heading.group(1)), index))
    out: list[tuple[str, int, int, int]] = []
    for position, (text, level, index) in enumerate(found):
        end = next((later for _t, later_level, later in found[position + 1 :] if later_level <= level), len(blocks))
        out.append((text, level, index, end))
    return out


def section_text(blocks: list[dict[str, Any]], start: int, end: int) -> str:
    return "\n".join(text for block in blocks[start + 1 : end] if (text := plain_text([block]).strip()))


def mentions(blocks: Iterable[dict[str, Any]]) -> int:
    def count(node: Any) -> int:
        if not isinstance(node, dict):
            return 0
        own = 1 if node.get("type") == "mention" else 0
        return own + sum(count(child) for child in node.get("children") or [])

    return sum(count(block) for block in blocks)


def is_pointer(text: str, links: int = 0) -> bool:
    """An opening that only points elsewhere: it starts "See …", names an event graph, a run record
    or a play-by-play, or is short and mostly links."""
    plain = text.strip()
    if not plain:
        return True
    if re.match(r"^see\b", plain, re.IGNORECASE) or POINTER_WORDS.search(plain):
        return True
    return links >= 2 and len(plain) < 200


def opening_of(blocks: list[dict[str, Any]]) -> Optional[tuple[int, int, str, int]]:
    """The Opening Situation section: (its index, end, text, links), or none."""
    for text, _level, index, end in sections(blocks):
        if OPENING.match(text):
            # The "Sources:" line a repair keeps below a written opening isn't the opening.
            body = [block for block in blocks[index + 1 : end] if not plain_text([block]).strip().startswith(SOURCES)]
            text = "\n".join(line for block in body if (line := plain_text([block]).strip()))
            return index, end, text, mentions(body)
    return None


def briefing_text(blocks: list[dict[str, Any]]) -> str:
    """A player briefing's first telling section (an Overview or how-to-use one passed over)."""
    for text, level, index, end in sections(blocks):
        # The title (h1) spans the whole note; its sections are what's told.
        if level > 1 and text and not OVERVIEW.match(text) and (body := section_text(blocks, index, end)):
            return body
    return ""


def written_opening(description: str, briefing: str) -> str:
    """An opening from the scenario's description (when it tells something) and the briefing's first
    telling section; empty when neither has anything."""
    parts = [part for part in ((description or "").strip(), (briefing or "").strip()) if len(part) >= MIN_TELLING and not is_pointer(part)]
    return "\n\n".join(parts)


def start_place(opening: str, locations: list[dict[str, Any]], persons: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Where play starts: the most specific place the opening names, narrowed to where most people
    within it are; with none named, where most people are; else the first place by name."""
    if not locations:
        return None
    by_id = {str(row["id"]): row for row in locations}

    def depth(row: dict[str, Any]) -> int:
        seen, level, parent = set(), 0, row.get("parent_id")
        while parent and str(parent) in by_id and str(parent) not in seen:
            seen.add(str(parent))
            level, parent = level + 1, by_id[str(parent)].get("parent_id")
        return level

    def within(root: str) -> set[str]:
        found, frontier = {root}, [root]
        while frontier:
            current = frontier.pop()
            for row in locations:
                if str(row.get("parent_id") or "") == current and str(row["id"]) not in found:
                    found.add(str(row["id"]))
                    frontier.append(str(row["id"]))
        return found

    people: dict[str, int] = {}
    for person in persons:
        if person.get("location_id"):
            people[str(person["location_id"])] = people.get(str(person["location_id"]), 0) + 1
    grams = text_grams(opening or "")
    named = [row for row in locations if set(record_keys(str(row.get("name") or ""), [str(one) for one in row.get("aliases") or []], [], False)) & grams]
    if named:
        best = max(named, key=lambda row: (depth(row), len(str(row.get("name") or "")), str(row["id"])))
        inside = within(str(best["id"]))
        crowded = max(inside, key=lambda one: (people.get(one, 0), one == str(best["id"]), str(by_id[one].get("name") or "")))
        return by_id[crowded] if people.get(crowded, 0) > people.get(str(best["id"]), 0) else best
    if people:
        top = max(people, key=lambda one: (people[one], one))
        if top in by_id:
            return by_id[top]
    return sorted(locations, key=lambda row: (str(row.get("name") or ""), str(row["id"])))[0]


REPAIR = "repair"  # the mark on each block a repair adds; unmended() takes them off again


def _paragraph(text: str, mark: str) -> dict[str, Any]:
    return {"type": "p", REPAIR: mark, "children": [{"text": text}]}


def mended_framing(blocks: list[dict[str, Any]], opening: Optional[str], place: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """The framing with a written Opening Situation in place of a pointer (the pointer kept below as
    "Sources:", its blocks verbatim) and a Starting Location section, each only where it is wanted.
    Every block it adds is marked, so unmended() gives back exactly what it was given."""
    out = [dict(block) for block in blocks]
    found = opening_of(out)
    if opening:
        written = [_paragraph(part, "opening") for part in opening.split("\n\n") if part.strip()]
        if found is None:
            out += [{"type": "h2", REPAIR: "opening", "children": [{"text": "Opening Situation"}]}, *written]
        else:
            index, end, _text, _links = found
            original = out[index + 1 : end]
            kept = [child for block in original for child in (block.get("children") or [])]
            sources = [{"type": "p", REPAIR: "sources", "original": original, "children": [{"text": f"{SOURCES} "}, *kept]}]
            out = out[: index + 1] + written + sources + out[end:]
    if place is not None and not any(START.match(text) for text, *_rest in sections(out)):
        out += [
            {"type": "h2", REPAIR: "start", "children": [{"text": "Starting Location"}]},
            {"type": "p", REPAIR: "start", "children": [{"type": "mention", "target_entity_type": "location", "target_entity_id": str(place["id"]), "children": [{"text": str(place.get("name") or "")}]}]},
        ]
    return out


def unmended(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A framing as it was before a repair: the blocks it added gone, the pointer's own blocks back."""
    out: list[dict[str, Any]] = []
    for block in blocks:
        mark = block.get(REPAIR)
        if mark == "sources":
            out += [dict(one) for one in block.get("original") or []]
        elif mark is None:
            out.append(block)
    return out


def scenario_problems(
    persons: list[dict[str, Any]], framing_blocks: Optional[list[dict[str, Any]]], locations: list[dict[str, Any]], sheetless: Optional[list[str]] = None
) -> list[str]:
    """What makes a scenario unplayable: people with no kind, no framing or an opening that only
    points elsewhere, no places, and (where the back end serves character sheets) a PC with none."""
    problems: list[str] = [f"{name} has no character sheet" for name in sorted(sheetless or [])]
    kindless = sorted(str(row.get("name") or row["id"]) for row in persons if not row.get("kind"))
    if kindless:
        problems.append(f"{len(kindless)} people have no kind: {', '.join(kindless[:5])}{'…' if len(kindless) > 5 else ''}")
    if framing_blocks is None:
        problems.append("no campaign framing")
    else:
        found = opening_of(framing_blocks)
        if found is None:
            problems.append("the framing has no Opening Situation")
        elif is_pointer(found[2], found[3]):
            problems.append(f"the Opening Situation only points elsewhere: {found[2][:120]!r}")
    if not locations:
        problems.append("no places")
    return problems


def is_framing_name(name: str) -> bool:
    return bool(FRAMING_NAME.search(name or ""))


def is_briefing(name: str) -> bool:
    return bool(BRIEFING.search(name or ""))
