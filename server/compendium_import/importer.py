# SPDX-License-Identifier: AGPL-3.0-or-later
"""A system's compendium into a setting's canon: every planned record (dnd5e.plan) made, or brought
up to date, as setting-wide canon with provenance official and its book and page in source.

A name is a record's identity within its type in the setting: a second run finds each by name and
changes only what differs, so the import is idempotent. Where two documents share a type and name
(a 2014 and a 2024 Goblin), they are one record: the newer text first, the other beneath under its
own heading, both sources named. New records are made in plural creates (chunked, Api.create_many),
then given their compendium UUIDs and numbers as private properties and their category as a tag."""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from compendium_import import dnd5e
from compendium_import.foundry import Document
from vault_import.api import Api
from vault_import.importer import Report
from vault_import.markdown import to_plate

COMPENDIUM_SOURCE = "Compendium source"
OFFICIAL = "official"
EDITION_LABELS = {"2024": "SRD 5.2.1 (2024)", "2014": "SRD 5.1 (2014)"}
ENTITIES = ("journal", "item", "location", "person")


@dataclass
class Merged:
    """The record one or more documents of a type and name become."""

    entity: str
    kind: str
    name: str
    texts: list[tuple[str, str]] = field(default_factory=list)  # (heading, markdown), newest first
    sources: list[str] = field(default_factory=list)
    uuids: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    stats: dict[str, str] = field(default_factory=dict)  # property key → JSON
    paths: list[str] = field(default_factory=list)
    picture: Optional[str] = None

    def markdown(self) -> str:
        first, *rest = self.texts or [("", "")]
        parts = [first[1]] + [f"## {heading}\n\n{text}" for heading, text in rest if text]
        return "\n\n".join(part for part in parts if part)

    def fields(self, setting_id: str) -> dict[str, Any]:
        unresolved: list[str] = []
        entry = to_plate(self.markdown(), lambda _name: None, unresolved) if self.markdown() else None
        values: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "setting_id": setting_id,
            "provenance": OFFICIAL,
            "source": "; ".join(self.sources)[:300],
            "entry": entry,
        }
        if self.keywords:
            values["keywords"] = self.keywords[:50]
        if self.picture:
            values["picture_url"] = self.picture
        return values


def merge(planned: list[tuple[Document, dnd5e.Planned]], order: list[str], labels: dict[str, str]) -> list[Merged]:
    """One record per type and name, the text of the edition (or line) first in ``order`` first,
    each other one beneath under its label."""
    rank = {edition: index for index, edition in enumerate(order)}
    ordered = sorted(planned, key=lambda pair: rank.get(pair[1].edition, len(order)))
    EDITION_LABELS = labels
    merged: dict[tuple[str, str], Merged] = {}
    for document, one in ordered:
        key = (one.entity, one.name.casefold())
        record = merged.get(key)
        if record is None:
            record = merged[key] = Merged(one.entity, one.kind, one.name)
        heading = EDITION_LABELS[one.edition] if record.texts else ""
        if one.markdown and all(one.markdown != text for _heading, text in record.texts):
            if record.texts and any(EDITION_LABELS[one.edition] == held for held, _text in record.texts[1:]):
                heading = f"{EDITION_LABELS[one.edition]}: {one.category or one.kind}"
            record.texts.append((heading, one.markdown))
        for value, into in ((one.source, record.sources), (one.uuid, record.uuids), *((tag, record.categories) for tag in [one.category, *one.tags])):
            if value and value not in into:
                into.append(value)
        record.keywords.extend(word for word in one.keywords if word not in record.keywords)
        stat = dnd5e.stat_property(one)
        if stat is not None and stat[0] not in record.stats:
            record.stats[stat[0]] = stat[1]
        record.paths.append(document.path)
        if record.picture is None and one.picture:
            record.picture = one.picture
    return list(merged.values())


@dataclass
class System:
    """What an import needs to know of a game system: how a document becomes a record, the order of
    its editions or lines (the first's text leads), their labels, and any attribution journal."""

    plan: Callable[[Document], tuple[Optional[dnd5e.Planned], Optional[str]]]
    order: list[str]
    labels: dict[str, str]
    attribution: Optional[Merged] = None


DND5E = System(
    dnd5e.plan,
    ["2024", "2014"],
    EDITION_LABELS,
    Merged("journal", "lore", dnd5e.ATTRIBUTION_NAME, texts=[("", dnd5e.ATTRIBUTION)], sources=[dnd5e.SRD_51, dnd5e.SRD_521], keywords=["licence", "attribution"]),
)


def wh40k_system() -> System:
    from compendium_import import wh40k

    return System(wh40k.plan, wh40k.ORDER, wh40k.LABELS)


class CompendiumImporter:
    def __init__(self, api: Api, setting_slug: str, dry_run: bool = False, system: Optional[System] = None) -> None:
        self.api = api
        self.setting_slug = setting_slug
        self.dry_run = dry_run
        self.system = system or DND5E
        self.report = Report()
        self._taxa: dict[str, str] = {}

    def _setting(self) -> str:
        found = [one for one in self.api.list("setting") if one.get("slug") == self.setting_slug]
        if not found:
            raise ValueError(f"No setting has the slug {self.setting_slug!r}")
        return str(found[0]["id"])

    def run(self, documents: list[Document]) -> Report:
        planned: list[tuple[Document, dnd5e.Planned]] = []
        for document in documents:
            one, why = self.system.plan(document)
            if one is None:
                self.report.skipped.append((document.path, why or "not imported"))
            else:
                planned.append((document, one))
        records = merge(planned, self.system.order, self.system.labels)
        if self.system.attribution is not None:
            records.append(self.system.attribution)
        setting_id = self._setting()
        for entity in ENTITIES:
            self._import(entity, [one for one in records if one.entity == entity], setting_id)
        return self.report

    def _import(self, entity: str, records: list[Merged], setting_id: str) -> None:
        held = {
            str(row["name"]).casefold(): row
            for row in self.api.list(entity, setting_id=setting_id)
            if not row.get("campaign_id")
        }
        new: list[Merged] = []
        for record in records:
            row = held.get(record.name.casefold())
            label = f"{entity} {record.name}"
            if row is None:
                new.append(record)
                self.report.created.append(label)
                continue
            changes = _changed(row, record.fields(setting_id))
            if not changes:
                self.report.unchanged.append(label)
            elif not self.dry_run:
                self.api.update(entity, str(row["id"]), **changes)
                self.report.updated.append(label)
            else:
                self.report.updated.append(label)
        if self.dry_run or not new:
            return
        made = self.api.create_many(entity, [record.fields(setting_id) for record in new])
        tags: list[dict[str, Any]] = []
        for record, row in zip(new, made):
            record_id = str(row["id"])
            self.api.add_property(entity, record_id, COMPENDIUM_SOURCE, json.dumps(record.uuids), is_private=True)
            for key, value in record.stats.items():
                self.api.add_property(entity, record_id, key, value, is_private=True)
            for category in record.categories:
                tags.append({"taxon_id": self._taxon(category, setting_id), "target_entity_type": entity, "target_entity_id": record_id})
        if tags:
            self.api.create_many("entity_taxon", tags)

    def _taxon(self, name: str, setting_id: str) -> str:
        """The setting's category of that name, made the first time."""
        if not self._taxa:
            self._taxa = {str(row["name"]): str(row["id"]) for row in self.api.list("taxon", setting_id=setting_id, kind="category") if not row.get("campaign_id")}
        if name not in self._taxa:
            self._taxa[name] = str(self.api.create("taxon", name=name, kind="category", setting_id=setting_id)["id"])
        return self._taxa[name]


def _changed(row: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
    """The fields that differ from the held row (entry and keywords compared as JSON)."""
    changed: dict[str, Any] = {}
    for name, value in fields.items():
        held = row.get(name)
        if name in ("entry", "keywords"):
            held = json.loads(held) if isinstance(held, str) and held else None
        if held != value and not (name == "setting_id" and held == value):
            changed[name] = value
    return changed
