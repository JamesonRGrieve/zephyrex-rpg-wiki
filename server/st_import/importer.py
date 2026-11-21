# SPDX-License-Identifier: AGPL-3.0-or-later
"""SillyTavern into the wiki, on vault_import's importer (its scope, properties, tags and report).

- A character card becomes a person (kind npc): its description (and scenario) the entry, its
  personality, first message and examples the AI voice, its tags the person's tags, its alternate
  greetings and creator notes private properties, its system prompt, post-history instructions,
  Character's Note and talkativeness the voice's own parts too, and a
  PNG card's image the person's picture (where the back end serves attachments). Its own lorebook
  (character_book) comes in as World Info.
- A World Info entry becomes a lore journal: its content the entry, its keys the keywords, its
  activation fields the lore block (S4d). A disabled entry is skipped and reported.

Each record keeps a private st_source property (file and card or entry), and a record found by name
in the scope is updated rather than made twice; a second run changes nothing.
"""

from typing import Any, Optional

from st_import.sillytavern import Card, Entry, book_entries, lore_of, voice_of
from zephyrex.extensions.wiki_shared.Lore import lore  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Names import names, voice  # type: ignore[import-not-found]
from vault_import.api import ApiError
from vault_import.importer import Importer, Placed, Report
from vault_import.markdown import to_plate
from vault_import.notes import Note

ST_SOURCE = "st_source"
# The system prompt, post-history instructions, Character's Note and talkativeness go to the voice.
PRIVATE_TEXTS = {"creator_notes": "Creator notes"}


class StImporter(Importer):
    def __init__(
        self, api: Any, campaign: Optional[str], setting_slug: Optional[str], setting_wide: bool = False, dry_run: bool = False
    ) -> None:
        super().__init__(api, setting_slug=setting_slug, dry_run=dry_run)
        self.campaign_name = campaign
        self.setting_wide = setting_wide
        self._attachments: Optional[bool] = None

    def _the_scope(self) -> dict[str, Optional[str]]:
        if self.setting_wide:
            return {"campaign_id": None, "setting_id": self._setting()}
        if not self.campaign_name:
            raise ValueError("Name the campaign (--campaign) or import as the setting's canon (--setting-wide)")
        return {"campaign_id": self._campaign(self.campaign_name), "setting_id": self._setting() if self.setting_slug else None}

    def _find_or_make(self, scope: dict[str, Optional[str]], kind: str, name: str, source: str, fields: dict[str, Any]) -> Optional[Placed]:
        names = self._index(scope)
        held = names.get(name)
        stand_in = Note(source, {}, "")
        if held is not None and held[0] == kind:
            return Placed(stand_in, kind, scope, held[1])
        if held is not None:
            self.report.refused.append((source, f"{name!r} is already a {held[0]} here"))
            return None
        if self.dry_run:
            record: dict[str, Any] = {"id": self._placeholder(), "name": name, **scope}
        else:
            record = self.api.create(kind, name=name, **fields, **scope)
        names[name] = (kind, record)
        self.report.created.append(f"{kind} {name}")
        return Placed(stand_in, kind, scope, record)

    def _write(self, placed: Placed, fields: dict[str, Any]) -> bool:
        """The record's fields as wanted; True when something changed."""
        changed = self._changed(placed, fields)
        if changed and not self.dry_run and not str(placed.record["id"]).startswith("(new"):
            placed.record = self.api.update(placed.kind, str(placed.record["id"]), **changed)
        return bool(changed)

    def _picture(self, card: Card, record_id: str) -> bool:
        if card.avatar is None or self.dry_run or record_id.startswith("(new"):
            return False
        if self._attachments is None:
            self._attachments = "attachments" in self.api.extensions()
        if not self._attachments:
            self.report.skipped.append((card.path, "its picture: this back end doesn't serve attachments yet"))
            return False
        if self.api.attachments("person", record_id, "primary_image"):
            return False
        asset = self.api.upload(f"{card.name}.png", "image/png", card.avatar)
        self.api.attach(str(asset["id"]), "person", record_id, "primary_image")
        return True

    def card(self, card: Card) -> None:
        scope = self._the_scope()
        placed = self._find_or_make(scope, "person", card.name, card.path, {"kind": "npc"})
        if placed is None:
            return
        record_id = str(placed.record["id"])
        made = f"person {card.name}" in self.report.created
        description = str(card.data.get("description") or "").strip()
        scenario = str(card.data.get("scenario") or "").strip()
        markdown = description + (f"\n\n## Scenario\n\n{scenario}" if scenario else "")
        unresolved: list[str] = []
        # As the server keeps them, so a second run compares like with like.
        fields: dict[str, Any] = {"entry": to_plate(markdown, self._resolver(scope), unresolved), "voice": voice(voice_of(card))}
        changed = self._write(placed, fields)
        changed |= self._property("person", record_id, ST_SOURCE, card.path, private=True)
        greetings = [str(one).strip() for one in card.data.get("alternate_greetings") or [] if str(one).strip()]
        if greetings:
            changed |= self._property("person", record_id, "Alternate greetings", "\n\n".join(greetings), private=True)
        for key, label in PRIVATE_TEXTS.items():
            text = str(card.data.get(key) or "").strip()
            if text:
                changed |= self._property("person", record_id, label, text, private=True)
        if not self.dry_run and not record_id.startswith("(new"):
            tagged = {one["taxon_id"] for one in self.api.list("entity_taxon", target_entity_type="person", target_entity_id=record_id)}
            for tag in [str(one).strip() for one in card.data.get("tags") or [] if str(one).strip()]:
                taxon = self._taxon(scope, tag, "tag")
                if taxon not in tagged:
                    self.api.create("entity_taxon", taxon_id=taxon, target_entity_type="person", target_entity_id=record_id)
                    tagged.add(taxon)
                    changed = True
        changed |= self._picture(card, record_id)
        if not made:
            (self.report.updated if changed else self.report.unchanged).append(f"person {card.name}")
        for entry in book_entries(card):
            self.entry(entry)

    def entry(self, entry: Entry) -> None:
        if entry.disabled:
            self.report.skipped.append((entry.source, "a disabled World Info entry"))
            return
        scope = self._the_scope()
        placed = self._find_or_make(scope, "journal", entry.name, entry.source, {"kind": "lore"})
        if placed is None:
            return
        made = f"journal {entry.name}" in self.report.created
        unresolved: list[str] = []
        fields = {
            "entry": to_plate(str(entry.fields.get("content") or ""), self._resolver(scope), unresolved),
            "keywords": names(entry.keys),
            "lore": lore(lore_of(entry.fields)),
        }
        changed = self._write(placed, fields)
        changed |= self._property("journal", str(placed.record["id"]), ST_SOURCE, entry.source, private=True)
        if not made:
            (self.report.updated if changed else self.report.unchanged).append(f"journal {entry.name}")

    def import_all(self, cards: list[Card], entries: list[Entry]) -> Report:
        for card in cards:
            try:
                self.card(card)
            except ApiError as error:
                self.report.refused.append((card.path, str(error.detail)))
        for entry in entries:
            try:
                self.entry(entry)
            except ApiError as error:
                self.report.refused.append((entry.source, str(error.detail)))
        return self.report
