# SPDX-License-Identifier: AGPL-3.0-or-later
"""The import itself, in two passes over the notes.

1. Each note's record, found in its scope by name (or by the vault path it was imported from) or
   created: a note with ``campaign: X`` belongs to campaign X (made in ``--setting`` when missing);
   one with ``setting_wide: true`` is that setting's canon (no campaign). Identity is per campaign
   by name (operator, 2026-11-21).
2. What each record says once every record exists: its entry (the Markdown, [[links]] as mentions),
   its parent or place, a journal's session, its tags, race and status, a person's organisation and
   dispositions, a hook's prerequisites, an item's holder, and the rest as properties.

Everything goes through the wiki's API, so its rules hold (a cycle, a wrong setting, an unknown
kind are refused and reported). A value already as the vault says is left alone, so a second run
changes nothing.
"""

import fcntl
import json
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterator, Optional

from vault_import.api import Api, ApiError
from zephyrex.extensions.wiki_shared.Contract import (  # type: ignore[import-not-found]
    FACTION_KINDS,
    GM_ONLY_PROPERTY,
    PLAY_STYLE,
    HOOK_KINDS,
    ITEM_KINDS,
    JOURNAL_KINDS,
    LOCATION_KINDS,
    PERSON_KINDS,
)
from zephyrex.extensions.wiki_shared.Names import names, unnamed_as_text, voice  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Pictures import picture_url  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Provenance import HOMEBREW, provenance  # type: ignore[import-not-found]
from vault_import.markdown import to_plate
from vault_import.notes import ENTITY_TYPES, PICTURE_TYPES, Note, link_name

VAULT_PATH = "vault_path"
# Frontmatter kept as a record's properties: key in the vault → (property key, value type).
PROPERTIES: dict[str, tuple[str, str]] = {
    "gender": ("Gender", "text"),
    "age": ("Age", "text"),
    "role": ("Role", "text"),
    "player": ("Player", "text"),
    "in_world_days": ("In-world days", "text"),
}
# A record's kind: `kind:`, or the vault's own field for it (location_type: facility, …).
KIND_FIELDS: dict[str, tuple[str, ...]] = {
    "location": ("location_type",),
    "person": ("person_type", "character_type"),
    "faction": ("faction_type", "organisation_type"),
    "item": ("item_type",),
    "journal": ("journal_type", "note_type"),
    "hook": ("quest_type",),
}
KINDS = {
    "location": LOCATION_KINDS,
    "person": PERSON_KINDS,
    "faction": FACTION_KINDS,
    "item": ITEM_KINDS,
    "journal": JOURNAL_KINDS,
    "hook": HOOK_KINDS,
}
# The vaults' words for a contract kind, where the word isn't the kind itself (after - becomes _).
KIND_SYNONYMS = {
    "hook": {"main": "major_quest", "side": "side_quest"},
    "journal": {"session": "session_report", "day_plan": "note", "gm_reference": "note", "investigation_framework": "note"},
    "item": {"equipment": "misc"},
}
# Handled elsewhere, or the note's identity; anything else in frontmatter is reported as unread.
READ = {
    "entity_type", "kind", "name", "campaign", "setting_wide", "is_private", "tags", "aliases", "status", "era",
    "race", "faction", "location", "relations", "parent_location", "parent", "parent_hook", "depends_on",
    "initial_build", "canonical_sheet",
    "holder", "quantity", "session_number", "session_date", "maps", "keywords", "voice", "provenance", "source", "image", "picture", "system", "editions", "description",
    "unnamed_as", "known",
    *PROPERTIES,
    *(one for fields in KIND_FIELDS.values() for one in fields),
}
STATUS_KIND = {"hook": "quest_status"}
# A setting's pregen (operator, 2026-11-21): the vault's vocabulary tags read as names, its
# lowercase role tag capitalised, and the tags that only repeat its type left out.
PREGEN_TAG = "pregen"
TAG_NAMES = {
    "pregen": "Pregen",
    "dark-heresy-2e": "Dark Heresy 2nd Edition",
    "dark-heresy-1e": "Dark Heresy",
    "dark-heresy": "Dark Heresy",
    "rogue-trader": "Rogue Trader",
    "deathwatch": "Deathwatch",
    "black-crusade": "Black Crusade",
    "only-war": "Only War",
    "imperium-maledictum": "Imperium Maledictum",
}
TYPE_TAGS = {"character", "pc", "person"}


def _tags(meta: dict[str, Any], kind: str) -> list[str]:
    """A note's tags as taxa names; a pregen's read as names (see TAG_NAMES)."""
    raw = [str(tag).strip() for tag in _list(meta.get("tags")) if _text(tag) and str(tag) != kind]
    if not any(tag.casefold() == PREGEN_TAG for tag in raw):
        return raw
    # The role's own name where its slug (or its last words') is the tag: "Astropath Transcendent
    # (Hive World)" names astropath-transcendent, "Deathwatch Tactical Marine (…)" tactical-marine.
    words = (_text(meta.get("role")) or "").split(" (")[0].split()
    by_slug = {re.sub(r"[^a-z0-9]+", "-", " ".join(words[start:]).casefold()).strip("-"): " ".join(words[start:]) for start in range(len(words))}
    named: list[str] = []
    for tag in raw:
        if tag.casefold() in TYPE_TAGS:
            continue
        name = TAG_NAMES.get(tag.casefold()) or by_slug.get(tag.casefold()) or (tag[:1].upper() + tag[1:] if tag == tag.lower() else tag)
        if name not in named:
            named.append(name)
    return named


def _sheet(value: Any) -> Optional[str]:
    """A character's build (the vault's initial_build: base64 of JSON, or JSON) as JSON text."""
    import base64

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    text = _text(value)
    if text is None:
        return None
    for decode in (lambda raw: base64.b64decode(raw, validate=True).decode("utf-8"), lambda raw: raw):
        try:
            return json.dumps(json.loads(decode(text)), ensure_ascii=False)
        except (ValueError, UnicodeDecodeError):
            continue
    return None


@dataclass
class Report:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    refused: list[tuple[str, str]] = field(default_factory=list)
    unresolved: dict[str, list[str]] = field(default_factory=dict)
    unread: dict[str, list[str]] = field(default_factory=dict)
    # Each campaign the run touched that still isn't playable (scenario_repair.rules.scenario_problems).
    unplayable: dict[str, list[str]] = field(default_factory=dict)

    def text(self, dry_run: bool) -> str:
        made = "would create" if dry_run else "created"
        lines = [
            f"{made}: {len(self.created)}, updated: {len(self.updated)}, unchanged: {len(self.unchanged)}, "
            f"skipped: {len(self.skipped)}, refused: {len(self.refused)}, notes with unresolved links: {len(self.unresolved)}"
        ]
        lines += [f"  skipped {path}: {why}" for path, why in self.skipped]
        lines += [f"  refused {path}: {why}" for path, why in self.refused]
        lines += [f"  unresolved in {path}: {', '.join(sorted(set(names)))}" for path, names in sorted(self.unresolved.items())]
        lines += [f"  unread in {path}: {', '.join(keys)}" for path, keys in sorted(self.unread.items())]
        lines += [f"  UNPLAYABLE {name}: {'; '.join(problems)}" for name, problems in sorted(self.unplayable.items())]
        return "\n".join(lines)


@dataclass
class Placed:
    """A note's record: where it lives and what it is."""

    note: Note
    kind: str
    scope: dict[str, Optional[str]]
    record: dict[str, Any]


def _style(name: str) -> str:
    """A play style's name as it's matched: "Combat heavy", "combat_heavy" and "combat-heavy" alike."""
    return "-".join(name.strip().lower().replace("_", " ").replace("-", " ").split())


def _text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _instant(value: Any) -> Optional[datetime]:
    """A stamp as an instant in UTC, however it was written (the server answers without a zone)."""
    if not value:
        return None
    moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return moment.astimezone(timezone.utc) if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _aliases_of(row: dict[str, Any]) -> list[str]:
    try:
        loaded = json.loads(row.get("aliases") or "[]")
    except json.JSONDecodeError:
        return []
    return [str(one) for one in loaded] if isinstance(loaded, list) else []


@contextmanager
def _shared_lock(name: str) -> Iterator[None]:
    """An exclusive lock shared by every importer process on this host (a lock file in the temp dir)."""
    path = Path(tempfile.gettempdir()) / f"vault_import-{name}.lock"
    with open(path, "w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class Importer:
    def __init__(
        self,
        api: Api,
        setting_slug: Optional[str] = None,
        dry_run: bool = False,
        log: Callable[[str], None] = print,
        force: bool = False,
        setting_name: Optional[str] = None,
    ) -> None:
        self.api = api
        self.setting_slug = setting_slug
        # A system-level import's setting, made when no setting has the slug (--setting-name).
        self.setting_name = setting_name
        self.dry_run = dry_run
        # Every matched record's fields written as the note gives them, changed or not (--force).
        self.force = force
        self.log = log
        self.report = Report()
        self.setting_id: Optional[str] = None
        self.campaigns: dict[str, str] = {}
        # Per scope key ("campaign:<id>" or "setting:<id>"): name → (kind, record).
        self.names: dict[str, dict[str, tuple[str, dict[str, Any]]]] = {}
        self._taxa: dict[tuple[str, str, str], str] = {}
        self._statuses: dict[tuple[str, str, str], str] = {}
        # Scopes whose taxa and statuses have been read (one list each, _known_labels).
        self._labels_read: set[str] = set()
        self._fresh = 0
        self._aliases: dict[str, list[tuple[str, tuple[str, dict[str, Any]]]]] = {}
        # A campaign's provenance and source, from its notes' frontmatter (homebrew when none says).
        self._provenance: dict[str, dict[str, Any]] = {}
        # A campaign's play-style tags, from its framing note's tags: (seeded ones matched, others made).
        self._play_styles: dict[str, list[str]] = {}
        # A campaign's framing: its description, game system and other editions (VTT's game systems by slug).
        self._framing: dict[str, dict[str, Any]] = {}
        self._campaign_rows: dict[str, dict[str, Any]] = {}
        self._touched: set[str] = set()
        # Pass 1's new records, by kind, made in one plural create each (_flush_new).
        self._new: dict[str, list[tuple[dict[str, Any], Note]]] = {}
        # Whether the back end serves attachments (asked once, when a first picture comes).
        self._attachments: Optional[bool] = None
        # Records this run created: nothing hangs off them yet, so their links are made without first
        # reading what they hold, and queued for one plural create per resource (_flush_pending).
        self._born: set[str] = set()
        self._pending: dict[str, list[tuple[dict[str, Any], str, str]]] = {}
        # Changes to rows already there, by resource: (the row as read, its new fields, note path, what),
        # saved in plural PUTs with each row's version (_flush_changes).
        self._changes: dict[str, list[tuple[dict[str, Any], dict[str, Any], str, str]]] = {}

    # ---- scope -----------------------------------------------------------------------------

    def _setting(self) -> str:
        if self.setting_id is None:
            if not self.setting_slug:
                raise ValueError("Name the setting these campaigns belong to: --setting <slug>")
            found = [one for one in self.api.list("setting") if one.get("slug") == self.setting_slug]
            system = bool(getattr(self.api, "system", False))
            if not found and system and self.setting_name:
                # A system setting made here, as SYSTEM (in a dry run, a placeholder).
                if self.dry_run:
                    self.setting_id = self._placeholder()
                else:
                    self.setting_id = str(self.api.create("setting", name=self.setting_name, slug=self.setting_slug)["id"])
                self.report.created.append(f"setting {self.setting_name}")
                return self.setting_id
            if not found:
                made_by = "--setting-name NAME to make it as SYSTEM" if system else f"make it first (POST /v1/setting {{\"setting\": {{\"name\": …, \"slug\": \"{self.setting_slug}\"}}}})"
                raise ValueError(f"No setting has the slug {self.setting_slug!r}: {made_by}")
            # The setting decides the level: a system import writes only into a system setting, an
            # owner's only into their own (operator, 2026-11-25: the SRD's content is system level;
            # "Private stuff is personal").
            if not self.api.mine(found[0]):
                if system:
                    raise ValueError(f"The setting {self.setting_slug!r} is an account's own: a system-level import (--system) writes only into a system setting")
                raise ValueError(f"The setting {self.setting_slug!r} isn't yours (a system setting is imported in process with --system)")
            self.setting_id = str(found[0]["id"])
        return self.setting_id

    def _campaign(self, name: str) -> str:
        if not self.campaigns:
            # A vault's campaigns are scenarios: a playthrough (one started from a scenario, which
            # carries its name) is never one of them, or a re-run would mark it a scenario.
            # A deleted one (a ROOT-run import lists those too) is never a match either.
            # And only the writer's own: SYSTEM sees every account's, an owner sees SYSTEM's scenarios.
            rows = [one for one in self.api.list("campaign") if not one.get("scenario_id") and not one.get("deleted_at") and self.api.mine(one)]
            self.campaigns = {str(one["name"]): str(one["id"]) for one in rows}
            self._campaign_rows = {str(one["name"]): one for one in rows}
        self._touched.add(name)
        if name not in self.campaigns:
            if self.dry_run:
                self.campaigns[name] = self._placeholder()
            else:
                made = self.api.create(
                    # A vault's campaign is a scenario: play starts a copy of it (copy on start).
                    "campaign", name=name, setting_id=self._setting() if self.setting_slug else None, is_scenario=True, **self._provenance_of(name)
                )
                self.campaigns[name] = str(made["id"])
                self._campaign_rows[name] = made
            self.report.created.append(f"campaign {name}")
        return self.campaigns[name]

    def _picture(self, kind: str, record_id: str, name: str, content_type: str, content: bytes, source: str) -> bool:
        """A record's picture (its primary_image, which world_entities returns), uploaded and attached
        when it has none; True when it was. Skipped and reported where the back end serves no
        attachments."""
        if self.dry_run or record_id.startswith("(new"):
            return False
        if self._attachments is None:
            self._attachments = "attachments" in self.api.extensions()
        if not self._attachments:
            self.report.skipped.append((source, "its picture: this back end doesn't serve attachments"))
            return False
        if record_id not in self._born and self.api.attachments(kind, record_id, "primary_image"):
            return False
        asset = self.api.upload(name, content_type, content)
        self.api.attach(str(asset["id"]), kind, record_id, "primary_image")
        return True

    def _provenance_of(self, name: str) -> dict[str, Any]:
        return self._provenance.get(name) or provenance({})

    def _gather_provenance(self, notes: list[Note]) -> None:
        """Each campaign's provenance and source, from its root note (its campaign_framing journal, one
        per campaign as the vaults write it); two that disagree are refused. Every other note's
        provenance is its own record's."""
        for note in notes:
            name = _text(note.meta.get("campaign"))
            word = _text(note.meta.get("kind")) or _text(note.meta.get("journal_type")) or ""
            if name is None or note.entity_type != "journal" or word.lower().replace("-", "_") != "campaign_framing":
                continue
            # Its tags are the campaign's play styles (the note's own kind and type words aside).
            plain = {_style(one) for one in ("journal", word, "framing", "campaign")}
            styles = [str(tag).strip() for tag in _list(note.meta.get("tags")) if _text(tag) and _style(str(tag)) not in plain]
            self._play_styles.setdefault(name, []).extend(one for one in styles if one not in self._play_styles.get(name, []))
            framing = self._framing.setdefault(name, {})
            if _text(note.meta.get("description")):
                framing["description"] = _text(note.meta.get("description"))
            if _text(note.meta.get("system")):
                framing["system"] = _text(note.meta.get("system"))
            editions = [str(one).strip() for one in _list(note.meta.get("editions")) if _text(one)]
            if editions:
                framing["editions"] = editions
            framing["path"] = note.path
            if "provenance" not in note.meta and "source" not in note.meta:
                continue
            try:
                wanted = provenance({"provenance": _text(note.meta.get("provenance")), "source": _text(note.meta.get("source"))})
            except ValueError as error:
                self.report.refused.append((note.path, str(error)))
                continue
            held = self._provenance.setdefault(name, wanted)
            if held != wanted:
                self.report.refused.append((note.path, f"campaign {name!r} is already {held['provenance']} here"))

    def _queue(self, resource: str, fields: dict[str, Any], path: str, label: str) -> None:
        """A row made later, in a plural create with the rest of its resource's (_flush_pending). The
        same row asked for twice is queued once: a quest that depends on an objective and the objective
        that names the quest as its parent are one hook_dependency, and a second copy would be refused
        as a duplicate and reported as if the vault were wrong."""
        queued = self._pending.setdefault(resource, [])
        if any(held == fields for held, _path, _label in queued):
            return
        queued.append((fields, path, label))

    def _flush_pending(self) -> None:
        """Every queued row, one plural create per resource and per BATCH; a refused row is reported
        against its own note, and the rest are written."""
        for resource in list(self._pending):
            queued = self._pending.pop(resource)
            outcomes = self.api.create_batch(resource, [fields for fields, _path, _label in queued])
            for (_fields, path, label), refusal in zip(queued, outcomes):
                if refusal is not None:
                    self.report.refused.append((path, f"{label}: {refusal}" if label else refusal))

    def _change(self, resource: str, row: dict[str, Any], fields: dict[str, Any], path: str, label: str) -> None:
        """A change to a row already there, saved later with the rest of its resource's (_flush_changes)."""
        self._changes.setdefault(resource, []).append((row, fields, path, label))

    def _flush_changes(self) -> None:
        """Every queued change, one plural PUT per resource and per BATCH, each row held to the version it
        was read at; a refused one is reported against its own note, and the rest are saved."""
        for resource in list(self._changes):
            queued = self._changes.pop(resource)
            outcomes = self.api.update_batch(resource, [(row, fields) for row, fields, _path, _label in queued])
            for (_row, _fields, path, label), refusal in zip(queued, outcomes):
                if refusal is not None:
                    self.report.refused.append((path, f"{label}: {refusal}" if label else refusal))

    def _flush_new(self) -> set[str]:
        """Pass 1's new records, one plural create per kind (contract order); each placeholder record
        is filled in place, so the name index and aliases already holding it see the real one.

        A plural create stops at the first record a hook refuses, the ones before it written. Then
        each queued record is looked up by name in its scope (adopted when it landed) or made alone,
        so a refusal is reported against its own note and nothing is made twice. Returns the paths
        of the notes refused."""
        refused: set[str] = set()
        for kind in ENTITY_TYPES:
            queued = self._new.pop(kind, [])
            fields = [{key: value for key, value in record.items() if key != "id"} for record, _note in queued]
            try:
                made: list[Optional[dict[str, Any]]] = list(self.api.create_many(kind, fields))
            except ApiError:
                made = [self._one_by_one(kind, one, note, refused) for one, (_record, note) in zip(fields, queued)]
            for (record, note), real in zip(queued, made):
                if real is None:
                    # Refused: links to it resolve to nothing rather than to a placeholder.
                    for index in self.names.values():
                        for name in [name for name, (_kind, held) in index.items() if held is record]:
                            del index[name]
                    continue
                record.clear()
                record.update(real)
                self._born.add(str(record["id"]))
                self._property(kind, str(record["id"]), VAULT_PATH, note.path, private=True)
        return refused

    def _one_by_one(self, kind: str, fields: dict[str, Any], note: Note, refused: set[str]) -> Optional[dict[str, Any]]:
        """A record a failed batch may or may not have written: found by name in its scope, or made."""
        scope = {key: fields.get(key) for key in ("campaign_id", "setting_id") if fields.get(key)}
        held = [row for row in self.api.list(kind, **scope) if row.get("name") == fields.get("name") and row.get("campaign_id") == fields.get("campaign_id")]
        if held:
            return held[0]
        try:
            return self.api.create(kind, **fields)
        except ApiError as error:
            self.report.refused.append((note.path, str(error.detail)))
            self.report.created.remove(f"{kind} {note.name}")
            refused.add(note.path)
            return None

    def _settle_framing(self) -> None:
        """A campaign's description, game system and editions as its framing note gives them. The
        system and editions are VTT's game systems by slug: set where the back end serves them
        (rpg_systems), reported and skipped where it doesn't; editions are kept as the campaign's
        "Editions" property (their ids, JSON), for an edition choice at the start."""
        wanted = {name: framing for name, framing in self._framing.items() if name in self._campaign_rows and len(framing) > 1}
        if not wanted or self.dry_run:
            return
        systems: Optional[dict[str, str]] = None
        for name, framing in sorted(wanted.items()):
            row = self._campaign_rows[name]
            changes: dict[str, Any] = {}
            if framing.get("description") and row.get("description") != framing["description"]:
                changes["description"] = framing["description"]
            slugs = [framing["system"]] if framing.get("system") else []
            slugs += framing.get("editions", [])
            if slugs and systems is None:
                systems = {str(one["slug"]): str(one["id"]) for one in self.api.list("game_system")} if "rpg_systems" in self.api.extensions() else {}
            if slugs and not systems:
                self.report.skipped.append((framing["path"], "its system and editions: this back end serves no game systems"))
            elif slugs:
                unknown = [slug for slug in slugs if slug not in (systems or {})]
                if unknown:
                    self.report.unresolved.setdefault(framing["path"], []).extend(f"game system {slug}" for slug in unknown)
                system = (systems or {}).get(framing.get("system") or "")
                if system and row.get("game_system_id") != system:
                    changes["game_system_id"] = system
                editions = [(systems or {})[slug] for slug in framing.get("editions", []) if slug in (systems or {})]
                if editions:
                    self._property("campaign", str(row["id"]), "Editions", json.dumps(editions))
            if changes:
                self._campaign_rows[name] = self.api.update("campaign", str(row["id"]), **changes)
                label = f"campaign {name}"
                if label not in self.report.created and label not in self.report.updated:
                    self.report.updated.append(label)

    def _settle_play_styles(self) -> None:
        """A campaign's play-style tags as its framing note gives them: a shared one (seeded) matched by
        name, any other made as one's own; tags already on the campaign stay."""
        wanted = {name: styles for name, styles in self._play_styles.items() if styles and name in self._campaign_rows}
        if not wanted or self.dry_run:
            return
        # Play styles are shared by every setting: vaults imported side by side take turns here, so two
        # never both make the same one.
        with _shared_lock("play-styles"):
            self._settle_play_styles_locked(wanted)

    def _settle_play_styles_locked(self, wanted: dict[str, list[str]]) -> None:
        # A system import uses SYSTEM's own (the seeded ones) only, never an account's.
        system = bool(getattr(self.api, "system", False))
        known = {_style(str(row["name"])): str(row["id"]) for row in self.api.list("taxon", kind=PLAY_STYLE) if not system or self.api.mine(row)}
        for name, styles in sorted(wanted.items()):
            campaign_id = str(self._campaign_rows[name]["id"])
            held = {str(row["taxon_id"]) for row in self.api.list("entity_taxon", target_entity_type="campaign", target_entity_id=campaign_id)}
            added = False
            for style in styles:
                taxon = known.get(_style(style))
                if taxon is None:
                    taxon = known[_style(style)] = str(self.api.create("taxon", name=style, kind=PLAY_STYLE)["id"])
                if taxon not in held:
                    self.api.create("entity_taxon", taxon_id=taxon, target_entity_type="campaign", target_entity_id=campaign_id)
                    held.add(taxon)
                    added = True
            label = f"campaign {name}"
            if added and label not in self.report.created and label not in self.report.updated:
                self.report.updated.append(label)

    def _settle_provenance(self) -> None:
        """A campaign the import touched, made what its notes say (homebrew when none says), and a
        scenario."""
        for name in sorted(self._touched):
            row = self._campaign_rows.get(name)
            if row is None or f"campaign {name}" in self.report.created:
                continue
            wanted = self._provenance_of(name)
            held = (row.get("provenance") or HOMEBREW, row.get("source"), bool(row.get("is_scenario")))
            if held == (wanted["provenance"], wanted["source"], True):
                continue
            if not self.dry_run:
                # "" clears a source the campaign no longer has; a vault's campaign is a scenario.
                self.api.update("campaign", str(row["id"]), provenance=wanted["provenance"], source=wanted["source"] or "", is_scenario=True)
            self.report.updated.append(f"campaign {name}")

    def _scope(self, note: Note) -> Optional[dict[str, Optional[str]]]:
        campaign = _text(note.meta.get("campaign"))
        if note.meta.get("setting_wide") is True:
            return {"campaign_id": None, "setting_id": self._setting()}
        if campaign is None:
            return None
        return {"campaign_id": self._campaign(campaign), "setting_id": self._setting() if self.setting_slug else None}

    @staticmethod
    def _key(scope: dict[str, Optional[str]]) -> str:
        return f"campaign:{scope['campaign_id']}" if scope["campaign_id"] else f"setting:{scope['setting_id']}"

    def _index(self, scope: dict[str, Optional[str]]) -> dict[str, tuple[str, dict[str, Any]]]:
        key = self._key(scope)
        if key not in self.names:
            names: dict[str, tuple[str, dict[str, Any]]] = {}
            self._aliases[key] = []
            if not str(scope["campaign_id"] or "").startswith("(new"):
                filters = {"campaign_id": scope["campaign_id"]} if scope["campaign_id"] else {"setting_id": scope["setting_id"]}
                for kind in ENTITY_TYPES:
                    for row in self.api.list(kind, **filters):
                        if row.get("deleted_at"):
                            continue
                        if scope["campaign_id"] or row.get("campaign_id") is None:
                            names.setdefault(str(row["name"]), (kind, row))
                            self._aliases[key].extend((alias, (kind, row)) for alias in _aliases_of(row))
            self.names[key] = names
        return self.names[key]

    def _alias_index(self, scope: dict[str, Optional[str]]) -> dict[str, tuple[str, dict[str, Any]]]:
        """The scope's records by the other names they go by (S4c), after their own names."""
        self._index(scope)
        return dict(reversed(self._aliases[self._key(scope)]))

    def _placeholder(self) -> str:
        self._fresh += 1
        return f"(new {self._fresh})"

    def _resolver(self, scope: dict[str, Optional[str]]) -> Callable[[str], Optional[tuple[str, str]]]:
        """A link's target: by name in the note's campaign, then in its setting's canon."""
        own = self._index(scope)
        canon = self._index({"campaign_id": None, "setting_id": scope["setting_id"]}) if scope["campaign_id"] and scope["setting_id"] else {}

        aliases = self._alias_index(scope)
        canon_aliases = self._alias_index({"campaign_id": None, "setting_id": scope["setting_id"]}) if canon else {}

        def resolve(name: str) -> Optional[tuple[str, str]]:
            found = own.get(name) or aliases.get(name) or canon.get(name) or canon_aliases.get(name)
            return None if found is None else (found[0], str(found[1]["id"]))

        return resolve

    def _kind(self, note: Note, entity: str) -> Optional[str]:
        """The note's kind, as the contract names it, or none; a word that isn't one is reported."""
        fields = ("kind", *KIND_FIELDS.get(entity, ()))
        field_name = next((one for one in fields if _text(note.meta.get(one))), "kind")
        word = _text(note.meta.get(field_name))
        if word is None:
            # A pregenerated or player character with no kind of its own is a PC.
            if entity == "person" and any(part in ("Pregens", "Players") for part in Path(note.path).parts):
                return "pc"
            # A vehicle note is a vessel.
            if entity == "location" and str(note.meta.get("entity_type") or "").strip().lower() == "vehicle":
                return "vessel"
            # Anyone else with no kind is an NPC (Sullenmire's people had none: no cast, no party).
            return "npc" if entity == "person" else None
        kind = word.strip().lower().replace("-", "_").replace(" ", "_")
        kind = KIND_SYNONYMS.get(entity, {}).get(kind, kind)
        if kind in KINDS.get(entity, ()):
            return kind
        self.report.unread.setdefault(note.path, []).append(f"{field_name}: {word} (not one of the {entity} kinds)")
        return "npc" if entity == "person" else None

    # ---- pass 1 ----------------------------------------------------------------------------

    def _place(self, note: Note) -> Optional[Placed]:
        kind = note.entity_type
        if kind not in ENTITY_TYPES:
            self.report.skipped.append((note.path, f"entity_type {kind!r} isn't one of {', '.join(ENTITY_TYPES)}"))
            return None
        scope = self._scope(note)
        if scope is None:
            self.report.skipped.append((note.path, "no campaign: and not setting_wide: true"))
            return None
        names = self._index(scope)
        held = names.get(note.name)
        placed_aliases = [str(one).strip() for one in _list(note.meta.get("aliases")) if _text(one)]
        if held is not None and held[0] == kind:
            self._aliases[self._key(scope)].extend((alias, (kind, held[1])) for alias in placed_aliases)
            return Placed(note, kind, scope, held[1])
        if held is not None:
            self.report.refused.append((note.path, f"{note.name!r} is already a {held[0]} in this campaign"))
            return None
        fields = {"name": note.name, "kind": self._kind(note, kind), **scope}
        record: dict[str, Any] = {"id": self._placeholder(), **fields}
        if not self.dry_run:
            # Made with the rest of its kind in one plural create (_flush_new), then filled in place.
            self._new.setdefault(kind, []).append((record, note))
        names[note.name] = (kind, record)
        self._aliases[self._key(scope)].extend((alias, (kind, record)) for alias in placed_aliases)
        self.report.created.append(f"{kind} {note.name}")
        return Placed(note, kind, scope, record)

    # ---- pass 2 ----------------------------------------------------------------------------

    def _property(self, kind: str, record_id: str, key: str, value: str, value_type: str = "text", private: bool = False) -> bool:
        """Sets a property; True when it changed something."""
        if self.dry_run or record_id.startswith("(new"):
            return False
        if record_id in self._born:
            # A born record's property is queued once (its vault path is set both when it is made and when
            # its links are), the last value winning.
            queued = self._pending.setdefault("record_metadata", [])
            body = {"target_entity_type": kind, "target_entity_id": record_id, "key": key, "value": value, "value_type": value_type, "is_private": private}
            # A refusal names the record (the note isn't known here).
            where = f"{kind} {record_id}"
            for index, (held, _path, _label) in enumerate(queued):
                if held["target_entity_id"] == record_id and held["key"] == key:
                    queued[index] = (body, where, f"property {key}")
                    return True
            self._queue("record_metadata", body, where, f"property {key}")
            return True
        held = {row["key"]: row for row in self.api.properties(kind, record_id)}
        if key not in held:
            self.api.add_property(kind, record_id, key, value, value_type, private)
            return True
        if held[key].get("value") != value:
            self._change("record_metadata", held[key], {"value": value}, f"{kind} {record_id}", f"property {key}")
            return True
        return False

    def _known_labels(self, scope: dict[str, Optional[str]]) -> None:
        """A scope's taxa and statuses, read once: one list of each, not one per name."""
        scope_key = self._key(scope)
        if scope_key in self._labels_read:
            return
        self._labels_read.add(scope_key)
        filters = {k: v for k, v in scope.items() if v}
        for one in self.api.list("taxon", **filters):
            self._taxa.setdefault((scope_key, str(one.get("kind")), str(one["name"])), str(one["id"]))
        for one in self.api.list("status", **filters):
            self._statuses.setdefault((scope_key, str(one.get("kind")), str(one["name"])), str(one["id"]))

    def _labels(self, placed: Placed) -> tuple[list[tuple[str, str]], list[str], Optional[tuple[str, str]]]:
        """What a note tags its record with, (name, taxon kind) each; the eras a framing note gives its
        campaign; and its status, (name, status kind)."""
        meta, kind = placed.note.meta, placed.kind
        # A framing note's tags are its campaign's play styles (_settle_play_styles), not its own.
        framing = kind == "journal" and (_text(meta.get("kind")) or _text(meta.get("journal_type")) or "").lower().replace("-", "_") == "campaign_framing"
        taxa = [] if framing else [(tag, "tag") for tag in _tags(meta, kind)]
        if _text(meta.get("race")):
            taxa.append((str(meta["race"]).strip(), "race"))
        # era: (one or a list): era-bound canon, or on a framing note its campaign's era (operator,
        # 2026-11-23: Reality's eras work like the 40k lines; era scoping in rpg_core).
        eras = [str(one).strip() for one in _list(meta.get("era")) if _text(one)]
        campaign_eras = eras if framing and placed.scope.get("campaign_id") else []
        if not campaign_eras:
            taxa += [(era, "era") for era in eras]
        status = _text(meta.get("status"))
        return taxa, campaign_eras, (None if status is None else (status, STATUS_KIND.get(kind, "entity_status")))

    def _make_labels(self, placed: list[Placed]) -> None:
        """Every tag, race, era and status the notes name that their scope lacks, made up front in one
        plural create per resource; linking them later is a lookup. A batch the server refuses is left
        to _taxon and _status, one at a time, so each refusal is its own."""
        wanted: dict[str, dict[tuple[str, str, str], dict[str, Any]]] = {"taxon": {}, "status": {}}
        for one in placed:
            self._known_labels(one.scope)
            scope_key = self._key(one.scope)
            taxa, campaign_eras, status = self._labels(one)
            for name, kind in taxa + [(era, "era") for era in campaign_eras]:
                if (scope_key, kind, name) not in self._taxa:
                    wanted["taxon"].setdefault((scope_key, kind, name), {"name": name, "kind": kind, **one.scope})
            if status is not None and (scope_key, status[1], status[0]) not in self._statuses:
                wanted["status"].setdefault((scope_key, status[1], status[0]), {"name": status[0], "kind": status[1], **one.scope})
        for resource, cache in (("taxon", self._taxa), ("status", self._statuses)):
            keys = list(wanted[resource])
            if not keys:
                continue
            try:
                made = self.api.create_many(resource, [wanted[resource][key] for key in keys])
            except ApiError:
                # Some may have landed before the refusal: the scopes are read again when next asked.
                self._labels_read.clear()
                continue
            for key, row in zip(keys, made):
                cache[key] = str(row["id"])

    def _taxon(self, scope: dict[str, Optional[str]], name: str, kind: str) -> str:
        key = (self._key(scope), kind, name)
        if key not in self._taxa:
            self._known_labels(scope)
        if key not in self._taxa:
            self._taxa[key] = str(self.api.create("taxon", name=name, kind=kind, **scope)["id"])
        return self._taxa[key]

    def _status(self, scope: dict[str, Optional[str]], name: str, kind: str) -> str:
        key = (self._key(scope), kind, name)
        if key not in self._statuses:
            self._known_labels(scope)
        if key not in self._statuses:
            self._statuses[key] = str(self.api.create("status", name=name, kind=kind, **scope)["id"])
        return self._statuses[key]

    def _fields(self, placed: Placed, resolve: Callable[[str], Optional[tuple[str, str]]]) -> dict[str, Any]:
        """The record's own fields as the note gives them."""
        meta, kind = placed.note.meta, placed.kind
        unresolved: list[str] = []
        fields: dict[str, Any] = {"entry": to_plate(placed.note.body, resolve, unresolved)}
        # Its picture by link (image: or picture:, an https address), shown before an uploaded one.
        link = _text(meta.get("picture")) or _text(meta.get("image"))
        if link is not None:
            try:
                fields["picture_url"] = picture_url(link)
            except ValueError as error:
                self.report.refused.append((placed.note.path, str(error)))
        # Where the record came from: its own provenance: and source: (homebrew when neither is given).
        try:
            fields.update(provenance({"provenance": _text(meta.get("provenance")), "source": _text(meta.get("source"))}))
        except ValueError as error:
            self.report.refused.append((placed.note.path, str(error)))
        aliases = [str(one).strip() for one in _list(meta.get("aliases")) if _text(one)]
        if aliases:
            # S4c: other names the record goes by, which link resolution and the AI's lorebook use.
            fields["aliases"] = names(aliases)
        keywords = [str(one).strip() for one in _list(meta.get("keywords")) if _text(one)]
        if keywords:
            fields["keywords"] = names(keywords)
        if kind == "person" and isinstance(meta.get("voice"), dict):
            # S4c: how the AI plays them; the server checks and fills the parts.
            given = meta["voice"]
            # As the server keeps it, so a second run compares like with like.
            fields["voice"] = voice({
                "personality": str(given.get("personality") or ""),
                "speech": str(given.get("speech") or ""),
                "first_message": str(given.get("first_message") or ""),
                "examples": [str(one) for one in _list(given.get("examples")) if _text(one)],
            })
        if kind == "person" and _text(meta.get("gender")):
            # Their gender on the record itself, beside the Gender property (operator, 2026-11-25:
            # "It's misgendering characters … Need pronoun enforcement").
            fields["gender"] = _text(meta.get("gender"))
        if kind == "person" and _text(meta.get("known")):
            # Known to the party by name from the start (a scenario's patron; operator, 2026-11-25).
            if _text(meta.get("known")) == "party":
                fields["known_to_party"] = True
            else:
                self.report.unread.setdefault(placed.note.path, []).append(f"known: {_text(meta.get('known'))} (only party is read)")
        if kind == "person" and _text(meta.get("unnamed_as")):
            # How they read to a party that doesn't know their name (operator, 2026-11-25).
            try:
                fields["unnamed_as"] = unnamed_as_text(_text(meta.get("unnamed_as")))
            except ValueError as error:
                self.report.unread.setdefault(placed.note.path, []).append(f"unnamed_as: {error}")
        if unresolved:
            self.report.unresolved[placed.note.path] = unresolved

        def ref(key: str, want: str) -> Optional[str]:
            name = link_name(meta.get(key))
            target = resolve(name) if name else None
            if name and (target is None or target[0] != want):
                self.report.unresolved.setdefault(placed.note.path, []).append(name)
                return None
            return target[1] if target else None

        if kind == "location":
            fields["parent_id"] = ref("parent_location", "location")
        elif kind == "faction":
            fields["parent_id"] = ref("parent", "faction")
        elif kind == "person":
            fields["location_id"] = ref("location", "location")
        elif kind == "journal":
            if meta.get("session_number") is not None:
                fields["session_number"] = int(meta["session_number"])
            when = meta.get("session_date")
            if isinstance(when, (date, datetime)):
                fields["occurred_at"] = datetime(when.year, when.month, when.day, tzinfo=timezone.utc).isoformat()
        elif kind == "hook" and _text(meta.get("status")) == "resolved" and not placed.record.get("resolved_at"):
            fields["resolved_at"] = datetime.now(timezone.utc).isoformat()
        return fields

    def _changed(self, placed: Placed, fields: dict[str, Any]) -> dict[str, Any]:
        record = placed.record
        changed: dict[str, Any] = {}
        for name, value in fields.items():
            if name in ("entry", "aliases", "keywords", "voice", "lore"):
                held = record.get(name)
                loaded = json.loads(held) if isinstance(held, str) and held else None
                if name == "entry" and placed.kind == "journal" and record.get("kind") == "campaign_framing" and isinstance(loaded, list):
                    # What scenario_repair added (a written opening, a starting place) isn't a change
                    # the vault made: compared without it, so a second run leaves the mended framing be.
                    from scenario_repair.rules import unmended

                    loaded = unmended(loaded)
                if loaded != value:
                    changed[name] = value
            elif name == "provenance":
                if (record.get(name) or HOMEBREW) != value:
                    changed[name] = value
            elif name == "picture_url":
                if (record.get(name) or None) != value:
                    changed[name] = value or ""
            elif name == "source":
                if record.get(name) != value:
                    # "" clears a source the note no longer gives.
                    changed[name] = value if value is not None else ""
            elif name in ("occurred_at", "resolved_at"):
                if value is not None and _instant(record.get(name)) != _instant(value):
                    changed[name] = value
            elif value is not None and record.get(name) != value:
                changed[name] = value
        return changed

    def _links(self, placed: Placed, resolve: Callable[[str], Optional[tuple[str, str]]]) -> bool:
        """Tags, race, status, organisation, dispositions, prerequisites, holder and properties."""
        meta, kind, scope = placed.note.meta, placed.kind, placed.scope
        record_id = str(placed.record["id"])
        changed = self._property(kind, record_id, VAULT_PATH, placed.note.path, private=True)
        for key, (label, value_type) in PROPERTIES.items():
            value = _text(meta.get(key))
            if value is not None:
                changed |= self._property(kind, record_id, label, value, value_type)
        if meta.get("is_private") is True:
            changed |= self._property(kind, record_id, GM_ONLY_PROPERTY, "true", "boolean", private=True)
        # A character's build and its sheet for the VTT, kept as they are, private.
        for key, label in (("initial_build", "Character sheet"), ("canonical_sheet", "Canonical sheet")):
            sheet = _sheet(meta.get(key))
            if sheet is not None:
                changed |= self._property(kind, record_id, label, sheet, private=True)
            elif meta.get(key) not in (None, ""):
                self.report.unread.setdefault(placed.note.path, []).append(f"{key} (not JSON or base64 JSON)")
        if self.dry_run or record_id.startswith("(new"):
            return changed
        born = record_id in self._born
        tagged = set() if born else {one["taxon_id"] for one in self.api.list("entity_taxon", target_entity_type=kind, target_entity_id=record_id)}
        wanted, campaign_eras, status_wanted = self._labels(placed)
        if campaign_eras:
            campaign_id = str(scope["campaign_id"])
            on_campaign = {one["taxon_id"] for one in self.api.list("entity_taxon", target_entity_type="campaign", target_entity_id=campaign_id)}
            for era in campaign_eras:
                taxon = self._taxon(scope, era, "era")
                if taxon not in on_campaign:
                    self._queue("entity_taxon", {"taxon_id": taxon, "target_entity_type": "campaign", "target_entity_id": campaign_id}, placed.note.path, f"its campaign's era {era}")
                    on_campaign.add(taxon)
                    changed = True
        for name, taxon_kind in wanted:
            taxon = self._taxon(scope, name, taxon_kind)
            if taxon not in tagged:
                self._queue("entity_taxon", {"taxon_id": taxon, "target_entity_type": kind, "target_entity_id": record_id}, placed.note.path, f"{taxon_kind} {name}")
                tagged.add(taxon)
                changed = True
        if status_wanted is not None:
            status = status_wanted[0]
            wanted_status = self._status(scope, status, status_wanted[1])
            held = [] if born else self.api.list("entity_status", target_entity_type=kind, target_entity_id=record_id)
            if not held:
                self._queue("entity_status", {"status_id": wanted_status, "target_entity_type": kind, "target_entity_id": record_id}, placed.note.path, f"status {status}")
                changed = True
            elif held[0]["status_id"] != wanted_status:
                self._change("entity_status", held[0], {"status_id": wanted_status}, placed.note.path, f"status {status}")
                changed = True
        if kind == "person":
            changed |= self._person_links(placed, resolve)
        elif kind == "hook":
            changed |= self._hook_links(placed, resolve)
        elif kind == "item":
            changed |= self._holder(placed, resolve)
        return changed

    def _person_links(self, placed: Placed, resolve: Callable[[str], Optional[tuple[str, str]]]) -> bool:
        meta, record_id, changed = placed.note.meta, str(placed.record["id"]), False
        born = record_id in self._born
        for name in [link_name(one) for one in _list(meta.get("faction"))]:
            target = resolve(name) if name else None
            if target is None or target[0] != "faction":
                if name:
                    self.report.unresolved.setdefault(placed.note.path, []).append(name)
                continue
            members = [] if born else self.api.list("relationship", person_id=record_id, target_faction_id=target[1])
            if not members:
                self._queue("relationship", {"person_id": record_id, "target_faction_id": target[1], "kind": "member"}, placed.note.path, f"member of {name}")
                changed = True
        held = [] if born else self.api.list("disposition", person_id=record_id)
        for relation in _list(meta.get("relations")):
            if not isinstance(relation, dict):
                continue
            name = link_name(relation.get("target"))
            target = resolve(name) if name else None
            if target is None or target[0] not in ("person", "faction"):
                if name:
                    self.report.unresolved.setdefault(placed.note.path, []).append(name)
                continue
            target_key = "target_person_id" if target[0] == "person" else "target_faction_id"
            if any(one.get(target_key) == target[1] and one.get("is_default") for one in held):
                continue
            self._queue(
                "disposition",
                {
                    "person_id": record_id,
                    "target_kind": target[0],
                    target_key: target[1],
                    "attitude": _text(relation.get("attitude")) or "neutral",
                    "note": _text(relation.get("note")),
                    "is_default": True,
                },
                placed.note.path,
                f"disposition toward {name}",
            )
            changed = True
        return changed

    def _hook_links(self, placed: Placed, resolve: Callable[[str], Optional[tuple[str, str]]]) -> bool:
        """A hook waits on what it depends on; a quest waits on the objectives that name it as parent."""
        meta, record_id, changed = placed.note.meta, str(placed.record["id"]), False
        edges = [(link_name(one), "prerequisite") for one in _list(meta.get("depends_on"))]
        edges.append((link_name(meta.get("parent_hook")), "parent"))
        for name, role in edges:
            target = resolve(name) if name else None
            if target is None or target[0] != "hook":
                if name:
                    self.report.unresolved.setdefault(placed.note.path, []).append(name)
                continue
            parent, child = (target[1], record_id) if role == "prerequisite" else (record_id, target[1])
            fresh = parent in self._born or child in self._born
            if fresh or not self.api.list("hook_dependency", parent_hook_id=parent, child_hook_id=child):
                self._queue("hook_dependency", {"parent_hook_id": parent, "child_hook_id": child}, placed.note.path, f"{role} {name}")
                changed = True
        return changed

    def _holder(self, placed: Placed, resolve: Callable[[str], Optional[tuple[str, str]]]) -> bool:
        meta, record_id = placed.note.meta, str(placed.record["id"])
        name = link_name(meta.get("holder"))
        target = resolve(name) if name else None
        if target is None:
            if name:
                self.report.unresolved.setdefault(placed.note.path, []).append(name)
            return False
        quantity = int(meta.get("quantity") or 1)
        instances = {str(one["id"]) for one in self.api.list("item_instance", item_id=record_id)}
        held = [one for one in self.api.list("entity_inventory", target_entity_type=target[0], target_entity_id=target[1]) if one.get("item_instance_id") in instances]
        if held:
            if held[0].get("quantity") != quantity:
                self._change("entity_inventory", held[0], {"quantity": quantity}, placed.note.path, "its quantity")
                return True
            return False
        owner = target[1] if target[0] == "person" else None
        instance = self.api.create("item_instance", item_id=record_id, owner_person_id=owner, quantity=quantity)
        self.api.create("entity_inventory", item_instance_id=str(instance["id"]), target_entity_type=target[0], target_entity_id=target[1], quantity=quantity)
        return True

    # ---- the run ---------------------------------------------------------------------------

    def run(self, notes: list[Note]) -> Report:
        placed: list[Placed] = []
        self._gather_provenance(notes)
        for note in notes:
            for problem in note.problems:
                self.report.skipped.append((note.path, problem))
            if note.problems:
                continue
            unread = sorted(key for key in note.meta if key not in READ)
            if unread:
                # Beside any kind word pass 1 couldn't read.
                self.report.unread.setdefault(note.path, []).extend(unread)
            try:
                found = self._place(note)
            except ApiError as error:
                self.report.refused.append((note.path, str(error.detail)))
                continue
            if found is not None:
                placed.append(found)
        if not self.dry_run:
            refused = self._flush_new()
            placed = [one for one in placed if one.note.path not in refused]
            self._make_labels(placed)
        created = {f"{one.kind} {one.note.name}" for one in placed}
        newly = set(self.report.created)
        for one in placed:
            label = f"{one.kind} {one.note.name}"
            try:
                resolve = self._resolver(one.scope)
                given = self._fields(one, resolve)
                fields = {key: value for key, value in given.items() if value is not None} if self.force and label not in newly else self._changed(one, given)
                if fields and not self.dry_run and not str(one.record["id"]).startswith("(new"):
                    self._change(one.kind, one.record, fields, one.note.path, "")
                linked = self._links(one, resolve)
                picture = one.note.picture
                if picture is not None:
                    content_type = PICTURE_TYPES[picture.suffix.lower()]
                    linked |= self._picture(one.kind, str(one.record["id"]), picture.name, content_type, picture.read_bytes(), one.note.path)
                if label not in newly and label in created:
                    (self.report.updated if (fields or linked) else self.report.unchanged).append(label)
            except ApiError as error:
                self.report.refused.append((one.note.path, str(error.detail)))
        if not self.dry_run:
            self._flush_pending()
            self._flush_changes()
        try:
            self._settle_provenance()
            self._settle_play_styles()
            self._settle_framing()
        except ApiError as error:
            self.report.refused.append(("(campaigns)", str(error.detail)))
        if not self.dry_run:
            self._mend_and_validate()
        return self.report

    def _mend_and_validate(self) -> None:
        """Each scenario the run touched mended as scenario_repair mends it (a pointer opening written
        out, a starting place), then checked: what still makes one unplayable is reported loudly."""
        from scenario_repair.repair import mend

        for name, campaign_id in sorted(self.campaigns.items()):
            try:
                campaign, _etag = self.api.get("campaign", campaign_id)
                if not campaign.get("is_scenario"):
                    continue
                problems = mend(self.api, campaign, True, dry_run=False).problems_after
            except ApiError as error:
                problems = [f"could not be checked: {error.detail}"]
            if problems:
                self.report.unplayable[name] = problems
