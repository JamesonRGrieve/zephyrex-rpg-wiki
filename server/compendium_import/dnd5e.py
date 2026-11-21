# SPDX-License-Identifier: AGPL-3.0-or-later
"""The dnd5e system's SRD packs as wiki records (plan approved by Zephyrex RPG, 2026-11-21):
creatures and vehicles are persons, gear is items, and spells, feats, classes and their features,
races, origins, backgrounds and the rules are lore journals with a category. Roll tables, active
effects, monster features (part of their monsters) and the starter heroes stay out."""

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from compendium_import.foundry import Document
from compendium_import.richtext import to_markdown

# The packs, in import order; the rest of the system's packs stay out.
PACKS = (
    "rules", "content24", "classes", "classes24", "subclasses", "classfeatures", "races", "origins24",
    "backgrounds", "feats24", "spells", "spells24", "items", "equipment24", "tradegoods", "monsters", "actors24",
)
SRD_51 = "D&D 5e SRD 5.1 (CC-BY-4.0)"
SRD_521 = "D&D 5e SRD 5.2.1 (CC-BY-4.0)"
ATTRIBUTION_NAME = "SRD attribution"
ATTRIBUTION = (
    "This work includes material taken from the System Reference Document 5.1 (“SRD 5.1”) by "
    "Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document. "
    "The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at "
    "https://creativecommons.org/licenses/by/4.0/legalcode.\n\n"
    "This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by Wizards "
    "of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the "
    "Creative Commons Attribution 4.0 International License, available at "
    "https://creativecommons.org/licenses/by/4.0/legalcode.\n\n"
    "The records here were read from the dnd5e system for Foundry VTT, whose packs carry the SRD text."
)
# A journal's category, by the system's item type (a taxon of kind category in the setting).
CATEGORIES = {
    "spell": "Spell",
    "feat": "Feature",
    "class": "Class",
    "subclass": "Subclass",
    "race": "Species",
    "background": "Background",
    "": "Rules",
}
ARMOUR = {"light", "medium", "heavy", "shield", "natural"}
ITEM_KINDS = {"weapon": "weapon", "consumable": "consumable", "container": "container", "loot": "misc", "tool": "misc"}
SCHOOLS = {"abj": "abjuration", "con": "conjuration", "div": "divination", "enc": "enchantment", "evo": "evocation", "ill": "illusion", "nec": "necromancy", "trs": "transmutation"}


@dataclass
class Planned:
    """A document as the wiki record it becomes: its type, kind, name, entry text, and the rest."""

    entity: str  # person, item or journal
    kind: str
    name: str
    markdown: str
    edition: str  # "2014" or "2024"
    source: str
    uuid: str
    category: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    stats: Optional[dict[str, Any]] = None
    # A real picture of it, by link (picture_url), where the pack gives one.
    picture: Optional[str] = None


def _description(document: Document) -> str:
    described = document.system.get("description")
    return str(described.get("value") or "") if isinstance(described, dict) else ""


def _edition(document: Document) -> str:
    source = document.system.get("source")
    rules = str(source.get("rules") or "") if isinstance(source, dict) else ""
    if rules in ("2014", "2024"):
        return rules
    return "2024" if document.pack.endswith("24") else "2014"


def _source(document: Document, edition: str) -> str:
    label = SRD_521 if edition == "2024" else SRD_51
    source = document.system.get("source")
    page = str(source.get("page") or "").strip() if isinstance(source, dict) else ""
    return f"{label}, p. {page}" if page else label


def _actor_markdown(document: Document) -> str:
    """A creature's text: its biography, then each of its features in turn."""
    parts: list[str] = []
    details = document.system.get("details") if isinstance(document.system.get("details"), dict) else {}
    biography = details.get("biography") if isinstance(details.get("biography"), dict) else {}
    if biography.get("value"):
        parts.append(to_markdown(str(biography["value"]), {"@name": document.name}))
    for item in document.data.get("items") or []:
        if not isinstance(item, dict):
            continue
        described = (item.get("system") or {}).get("description")
        name = str(item.get("name") or "").strip()
        lookups = {"@name": document.name, "@item.name": name}
        text = to_markdown(str(described.get("value") or ""), lookups) if isinstance(described, dict) else ""
        if name and text:
            parts.append(f"**{name}.** {text}" if "\n" not in text else f"#### {name}\n\n{text}")
        elif name:
            parts.append(f"**{name}.**")
    return "\n\n".join(part for part in parts if part)


def _stat_block(document: Document) -> dict[str, Any]:
    """A creature's numbers, kept as a private property (the VTT plays them; the wiki shows them)."""
    system = document.system
    details = system.get("details") if isinstance(system.get("details"), dict) else {}
    attributes = system.get("attributes") if isinstance(system.get("attributes"), dict) else {}
    creature = details.get("type") if isinstance(details.get("type"), dict) else {}
    hp = attributes.get("hp") if isinstance(attributes.get("hp"), dict) else {}
    ac = attributes.get("ac") if isinstance(attributes.get("ac"), dict) else {}
    abilities = system.get("abilities") if isinstance(system.get("abilities"), dict) else {}
    traits = system.get("traits") if isinstance(system.get("traits"), dict) else {}
    block = {
        "cr": details.get("cr"),
        "type": " ".join(str(part) for part in (creature.get("value"), creature.get("subtype")) if part) or None,
        "size": traits.get("size"),
        "alignment": details.get("alignment") or None,
        "ac": ac.get("flat") or ac.get("value"),
        "hp": hp.get("max") or hp.get("value"),
        "hp_formula": hp.get("formula") or None,
        "abilities": {key: value.get("value") for key, value in abilities.items() if isinstance(value, dict)},
    }
    return {key: value for key, value in block.items() if value not in (None, {}, "")}


def plan(document: Document) -> tuple[Optional[Planned], Optional[str]]:
    """The record ``document`` becomes, or why it stays out."""
    if not document.name:
        return None, "no name"
    edition = _edition(document)
    common = {"name": document.name, "edition": edition, "source": _source(document, edition), "uuid": document.uuid}
    if document.document_type == "JournalEntry":
        pages = [page for page in document.data.get("pages") or [] if isinstance(page, dict)]
        sections = []
        for page in sorted(pages, key=lambda one: one.get("sort") or 0):
            # A text page's HTML, or a class, subclass or spell-list page's description.
            content = (page.get("text") or {}).get("content") or ((page.get("system") or {}).get("description") or {}).get("value") or ""
            text = to_markdown(str(content), {"@name": document.name})
            title = str(page.get("name") or "").strip()
            if text:
                sections.append(f"## {title}\n\n{text}" if title and title != document.name and len(pages) > 1 else text)
        return Planned("journal", "lore", markdown="\n\n".join(sections), category="Rules", keywords=["rules"], **common), None
    if document.document_type == "Actor":
        if document.type == "character":
            return None, "a starter hero (a player character, not canon)"
        kind = "vehicle" if document.type == "vehicle" else "monster"
        creature = (document.system.get("details") or {}).get("type") if isinstance(document.system.get("details"), dict) else None
        category = str(creature.get("value") or "").title() if isinstance(creature, dict) and creature.get("value") else None
        return Planned("person", kind, markdown=_actor_markdown(document), category=category, stats=_stat_block(document), **common), None
    if document.document_type != "Item":
        return None, f"a {document.document_type} (roll tables and effects stay out)"
    text = to_markdown(_description(document), {"@name": document.name, "@item.name": document.name})
    if document.type in CATEGORIES:
        keywords = [CATEGORIES[document.type].lower()]
        if document.type == "spell":
            level = document.system.get("level")
            school = SCHOOLS.get(str(document.system.get("school") or ""), "")
            keywords += [f"level {level}" if level else "cantrip"] + ([school] if school else [])
        return Planned("journal", "lore", markdown=text, category=CATEGORIES[document.type], keywords=keywords, **common), None
    if document.type == "equipment":
        armour = (document.system.get("type") or {}).get("value") if isinstance(document.system.get("type"), dict) else None
        return Planned("item", "armour" if armour in ARMOUR else "misc", markdown=text, **common), None
    if document.type in ITEM_KINDS:
        return Planned("item", ITEM_KINDS[document.type], markdown=text, **common), None
    return None, f"an item of type {document.type!r}"


def stat_property(planned: Planned) -> Optional[tuple[str, str]]:
    """The private property that keeps a creature's numbers: its key and JSON value."""
    if not planned.stats:
        return None
    return f"Stat block ({planned.edition})", json.dumps(planned.stats, ensure_ascii=False, sort_keys=True)
