# SPDX-License-Identifier: AGPL-3.0-or-later
"""The wh40k-rpg system's official packs (dh-campaign/.foundry-system/src/packs-private/<line>/<pack>)
as wiki records for the warhammer-40000 setting (plan approved by Zephyrex RPG, 2026-11-21).

Only what the printed books hold comes in: a document's sources are its system.source.<line>
entries whose provenance is "raw", each "<book>, p. <page>"; one with none stays out (homebrew,
derived). Its text is its first raw line's (lines in LINES order, DH2 first). Actors are persons,
voidcraft places (vessel) and other craft persons (vehicle), gear items, and talents, traits,
powers, qualities, skills, origins and the rules lore journals with a category. Roll tables,
adventures, Imperium Maledictum's endeavours and patrons, and the homebrew packs stay out."""

import json
import re
from pathlib import Path
from typing import Any, Optional

from compendium_import.dnd5e import Planned
from compendium_import.foundry import Document
from compendium_import.richtext import to_markdown

SYSTEM_ID = "wh40k-rpg"
# The game lines in import order (DH2 first, as dh-campaign plays it), each with its folder and label.
LINES: tuple[tuple[str, str, str], ...] = (
    ("dh2", "dark-heresy-2", "Dark Heresy 2nd Edition"),
    ("dh1", "dark-heresy-1", "Dark Heresy"),
    ("rt", "rogue-trader", "Rogue Trader"),
    ("dw", "deathwatch", "Deathwatch"),
    ("bc", "black-crusade", "Black Crusade"),
    ("ow", "only-war", "Only War"),
    ("im", "imperium-maledictum", "Imperium Maledictum"),
)
ORDER = [code for code, _folder, _label in LINES]
LABELS = {code: label for code, _folder, label in LINES}
PACK = re.compile(r"^(?P<line>[a-z0-9]+)-(?P<book>[a-z0-9]+)-(?P<group>actors|items|origins|journals|vehicles|locations)(?:-(?P<content>.+))?$")
DOCUMENT_TYPES = {"actors": "Actor", "vehicles": "Actor", "items": "Item", "origins": "Item", "locations": "Item", "journals": "JournalEntry"}
ITEM_KINDS = {
    "weapon": "weapon",
    "armour": "armour",
    "ammunition": "consumable",
    "gear": "misc",
    "cybernetic": "misc",
    "weaponModification": "misc",
    "armourModification": "misc",
    "shipComponent": "misc",
    "shipWeapon": "misc",
    "vehicleUpgrade": "misc",
    "medal": "misc",
}
LORE_CATEGORIES = {
    "talent": "Talent",
    "trait": "Trait",
    "weaponQuality": "Weapon quality",
    "psychicPower": "Psychic power",
    "skill": "Skill",
    "order": "Order",
    "criticalInjury": "Critical injury",
    "mutation": "Mutation",
    "vehicleTrait": "Vehicle trait",
    "condition": "Condition",
    "specialAbility": "Special ability",
    "navigatorPower": "Navigator power",
    "ritual": "Ritual",
    "shipRole": "Ship role",
    "malignancy": "Malignancy",
}
ORIGIN_CATEGORIES = {"homeworlds": "Homeworld", "backgrounds": "Background", "roles": "Role", "careers": "Career", "elite-advances": "Elite advance", "regiments": "Regiment", "specialities": "Speciality", "specialties": "Speciality", "archetypes": "Archetype", "motivations": "Motivation", "pride": "Pride", "disgrace": "Disgrace", "birthrights": "Birthright", "lures": "Lure", "trials": "Trial"}
LOCATION_KINDS = {"system", "planet", "moon", "continent", "region", "city", "district", "building", "facility", "room", "vessel"}
STAT_KEYS = ("characteristics", "wounds", "armourPoints", "armour", "move", "size", "threatLevel", "speed", "integrity", "manoeuverability", "crew")


def read_lines(root: Path, lines: Optional[list[str]] = None) -> list[Document]:
    """Every official pack's documents of ``lines`` (folder names; all of LINES when none), in line
    order. Folders and nameless files are left out; a pack outside the naming scheme too."""
    wanted = lines or [folder for _code, folder, _label in LINES]
    documents: list[Document] = []
    for folder in wanted:
        if not (root / folder).is_dir():
            continue
        for pack_dir in sorted((root / folder).iterdir()):
            match = PACK.match(pack_dir.name)
            source = pack_dir / "_source"
            if match is None or not source.is_dir():
                continue
            document_type = DOCUMENT_TYPES[match.group("group")]
            for path in sorted(source.rglob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or str(data.get("_key", "")).startswith("!folders") or not data.get("_id") or not data.get("name"):
                    continue
                uuid = f"Compendium.{SYSTEM_ID}.{pack_dir.name}.{document_type}.{data['_id']}"
                documents.append(Document(pack_dir.name, document_type, data, str(path.relative_to(root)), uuid))
    return documents


def _raw_sources(document: Document) -> list[tuple[str, str]]:
    """(line, "<book>, p. <page>") for each printed-book source, in LINES order."""
    source = document.system.get("source")
    found: list[tuple[str, str]] = []
    if not isinstance(source, dict):
        return found
    for line in sorted(source, key=lambda code: ORDER.index(code) if code in ORDER else len(ORDER)):
        entry = source[line]
        if isinstance(entry, dict) and entry.get("provenance") == "raw" and entry.get("book"):
            page = str(entry.get("page") or "").strip()
            found.append((line, f"{entry['book']}, p. {page}" if page else str(entry["book"])))
    return found


def _line_text(value: Any, line: str) -> str:
    """A per-line field's HTML for ``line`` (its own, or the field itself when it isn't per-line)."""
    if isinstance(value, dict) and line in value:
        value = value[line]
    if isinstance(value, dict):
        value = value.get("value")
    return str(value) if isinstance(value, str) else ""


def _picture(document: Document) -> Optional[str]:
    """Its image when it's a real picture (an https link that isn't a generic game icon)."""
    image = str(document.data.get("img") or "")
    if not image.startswith("https://") or "game-icons" in image or len(image) > 2000:
        return None
    return image


def _stats(document: Document, line: str) -> Optional[dict[str, Any]]:
    block: dict[str, Any] = {}
    for key in STAT_KEYS:
        value = document.system.get(key)
        if isinstance(value, dict) and line in value:
            value = value[line]
        if value not in (None, "", {}, []):
            block[key] = value
    return block or None


def plan(document: Document) -> tuple[Optional[Planned], Optional[str]]:
    """The record ``document`` becomes, or why it stays out."""
    raw = _raw_sources(document)
    if not raw:
        return None, "no printed-book (raw) source"
    match = PACK.match(document.pack)
    group = match.group("group") if match else ""
    content = (match.group("content") or "") if match else ""
    line = raw[0][0]
    if document.document_type == "JournalEntry":
        pages = [page for page in document.data.get("pages") or [] if isinstance(page, dict)]
        sections = []
        for page in sorted(pages, key=lambda one: one.get("sort") or 0):
            text = to_markdown(str((page.get("text") or {}).get("content") or ""))
            title = str(page.get("name") or "").strip()
            if text:
                sections.append(f"## {title}\n\n{text}" if title and title != document.name and len(pages) > 1 else text)
        markdown = "\n\n".join(sections)
    else:
        markdown = to_markdown(_line_text(document.system.get("description"), line), {"@name": document.name})
    common = {
        "name": document.name,
        "markdown": markdown,
        "edition": line,
        "source": "; ".join(label for _line, label in raw),
        "uuid": document.uuid,
    }
    kind_type = document.type
    if group in ("actors", "vehicles"):
        if kind_type.endswith("voidcraft"):
            planned = Planned("location", "vessel", category="Voidcraft", **common)
        elif kind_type.endswith(("terracraft", "aircraft")):
            planned = Planned("person", "vehicle", category="Vehicle", stats=_stats(document, line), **common)
        else:
            kind = "creature" if "mounts" in content else "npc"
            planned = Planned("person", kind, stats=_stats(document, line), **common)
    elif group == "journals":
        planned = Planned("journal", "lore", category="Rules", keywords=["rules"], **common)
    elif group == "origins":
        category = ORIGIN_CATEGORIES.get(content, "Origin")
        planned = Planned("journal", "lore", category=category, keywords=[category.lower()], **common)
    elif group == "locations" or kind_type == "location":
        held = str(document.system.get("locationType") or "")
        planned = Planned("location", held if held in LOCATION_KINDS else "region", **common)
    elif kind_type in ITEM_KINDS:
        planned = Planned("item", ITEM_KINDS[kind_type], **common)
    elif kind_type in LORE_CATEGORIES:
        category = LORE_CATEGORIES[kind_type]
        planned = Planned("journal", "lore", category=category, keywords=[category.lower()], **common)
    else:
        return None, f"an item of type {kind_type!r}"
    planned.picture = _picture(document)
    return planned, None
