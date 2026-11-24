# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core extension definition: depends on genealogy (Person) and world_spatial (Location), and
nothing depends back on it from Tier 1 (operator, 2026-11-20)."""

from datetime import datetime
from typing import Any, ClassVar, Optional

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension, ability
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class RPGCoreExtension(AbstractStaticExtension):
    name: ClassVar[str] = "rpg_core"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Campaigns; widens Person into the character table and scopes world records to a campaign"
    )
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(
                name="genealogy",
                friendly_name="Genealogy",
                optional=False,
                reason="rpg_core widens genealogy's Person into the character table",
            ),
            EXT_Dependency(
                name="world_spatial",
                friendly_name="World: places",
                optional=False,
                reason="rpg_core scopes locations to a campaign, and a person stands in a location",
            ),
            EXT_Dependency(
                name="world_social",
                friendly_name="World: organisations",
                optional=False,
                reason="rpg_core scopes factions to a campaign",
            ),
            EXT_Dependency(
                name="world_inventory",
                friendly_name="World: items",
                optional=False,
                reason="rpg_core scopes items to a campaign",
            ),
            EXT_Dependency(
                name="world_narrative",
                friendly_name="World: journals",
                optional=False,
                reason="rpg_core scopes journals to a campaign and writes session reports",
            ),
            EXT_Dependency(
                name="world_taxonomy",
                friendly_name="World: taxonomy",
                optional=False,
                reason="rpg_core scopes tags, categories and statuses to a campaign",
            ),
            EXT_Dependency(
                name="world_properties",
                friendly_name="World: property kits",
                optional=False,
                reason="rpg_core scopes property kits to a campaign or setting, and copies a template's properties",
            ),
            EXT_Dependency(
                name="attachments",
                friendly_name="Attachments",
                optional=True,
                reason="A record's picture (world_entities.picture) is its primary_image attachment",
            ),
            EXT_Dependency(
                name="acl_rbac",
                friendly_name="ACL / RBAC",
                optional=True,
                reason="Per-row visibility for GM-secret records",
            ),
        ]
    )

    # rpg-ai A24 calls these through loaded_ability(model_registry, "rpg_core", name). The caller
    # passes the registry and whose permissions they act with (the campaign's GM).

    @classmethod
    @ability("session_report")
    def session_report(
        cls,
        model_registry: Any,
        requester_id: str,
        campaign_id: str,
        title: str,
        body: str | list[Any],
        occurred_at: Optional[datetime] = None,
        session_number: Optional[int] = None,
        mentions: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, str]:
        """Write a session report into the campaign as a journal; ``{"id": ...}``."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import (  # type: ignore[import-not-found]
            SessionReportIn,
            write_session_report,
        )

        report = SessionReportIn(
            campaign_id=campaign_id,
            title=title,
            body=body,
            occurred_at=occurred_at,
            session_number=session_number,
            mentions=mentions or [],
        )
        return {"id": write_session_report(model_registry, requester_id, report)}

    @classmethod
    @ability("session_report_get")
    def session_report_get(cls, model_registry: Any, requester_id: str, report_id: str) -> dict[str, Any]:
        """A session report as its review sheet reads it."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import read_session_report  # type: ignore[import-not-found]

        return read_session_report(model_registry, requester_id, report_id).model_dump(mode="json")

    @classmethod
    @ability("world_entities")
    def world_entities(
        cls,
        model_registry: Any,
        requester_id: str,
        campaign_id: str,
        since: Optional[datetime] = None,
        kinds: Optional[list[str]] = None,
        after: Optional[str] = None,
        limit: int = 100,
        include_setting: bool = False,
    ) -> dict[str, Any]:
        """A campaign's changed entities since a time, tombstones included (rpg-ai A15); with
        include_setting, its setting's canon too (S6)."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import world_entities  # type: ignore[import-not-found]

        return world_entities(model_registry, requester_id, campaign_id, since, kinds, after, limit, include_setting).model_dump(mode="json")

    @classmethod
    @ability("setting_canon")
    def setting_canon(
        cls,
        model_registry: Any,
        requester_id: str,
        setting_id: str,
        since: Optional[datetime] = None,
        kinds: Optional[list[str]] = None,
        after: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """A setting's canon (its records with no campaign) changed since a time, tombstones included
        (S6): what rpg-ai's canon notices check against."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import setting_canon  # type: ignore[import-not-found]

        return setting_canon(model_registry, requester_id, setting_id, since, kinds, after, limit).model_dump(mode="json")

    @classmethod
    @ability("plot_state")
    def plot_state(cls, model_registry: Any, requester_id: str, campaign_id: str) -> list[dict[str, Any]]:
        """Each of a campaign's hooks with its state (W57): resolved, available, needs_check or blocked."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import plot_state  # type: ignore[import-not-found]

        return [hook.model_dump(mode="json") for hook in plot_state(model_registry, requester_id, campaign_id)]

    @classmethod
    @ability("world_entities_by_id")
    def world_entities_by_id(cls, model_registry: Any, requester_id: str, ids: list[str]) -> dict[str, Any]:
        """The named records, shaped as world_entities shapes them, under the requester's access; an id
        they can't see is absent (rpg-ai's sandbox cast)."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import world_entities_by_id  # type: ignore[import-not-found]

        return world_entities_by_id(model_registry, requester_id, ids).model_dump(mode="json")

    @classmethod
    @ability("instantiate_campaign")
    def instantiate_campaign(
        cls, model_registry: Any, requester_id: str, source_campaign_id: str, name: Optional[str] = None, pregens: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Copy on start: a playthrough of the scenario, with the setting's pregens picked (person
        ids) copied in too, {campaign, id_map} (source id → copy id)."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import instantiate_campaign  # type: ignore[import-not-found]

        return instantiate_campaign(model_registry, requester_id, source_campaign_id, name, pregens=pregens).model_dump(mode="json")

    @classmethod
    @ability("setting_pregens")
    def setting_pregens(cls, model_registry: Any, requester_id: str, setting_id: str) -> dict[str, Any]:
        """The setting's pregenerated player characters: {pregens: [{id, name, summary, picture_url,
        tags, source}]} (canon pcs tagged Pregen), for a party picker."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import setting_pregens  # type: ignore[import-not-found]

        return setting_pregens(model_registry, requester_id, setting_id).model_dump(mode="json")

    @classmethod
    @ability("campaign_clock")
    def campaign_clock(cls, model_registry: Any, requester_id: str, campaign_id: str) -> dict[str, Any]:
        """The campaign's in-world clock: {minutes, day, time} (day 1, 08:00 until advanced)."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import campaign_clock  # type: ignore[import-not-found]

        return campaign_clock(model_registry, requester_id, campaign_id).model_dump(mode="json")

    @classmethod
    @ability("advance_clock")
    def advance_clock(cls, model_registry: Any, requester_id: str, campaign_id: str, minutes: int, reason: Optional[str] = None) -> dict[str, Any]:
        """Its clock moved on (the campaign's GM's to do): {minutes, day, time, reason}."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import advance_clock  # type: ignore[import-not-found]

        return advance_clock(model_registry, requester_id, campaign_id, minutes, reason).model_dump(mode="json")

    @classmethod
    @ability("move_person")
    def move_person(cls, model_registry: Any, requester_id: str, person_id: str, location_id: str, reason: Optional[str] = None) -> dict[str, Any]:
        """A person moved by the GM, to a place in their campaign or its setting, recorded in their
        history: {person_id, from, to, at: {minutes, day, time} | null, reason}."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import move_person  # type: ignore[import-not-found]

        return move_person(model_registry, requester_id, person_id, location_id, reason).model_dump(mode="json", by_alias=True)

    @classmethod
    @ability("ensure_person")
    def ensure_person(cls, model_registry: Any, requester_id: str, campaign_id: str, name: str, summary: Optional[str] = None) -> dict[str, Any]:
        """The campaign's person called ``name`` (case aside), or a new NPC made GM only and in play,
        ``summary`` its entry: {id, name, created} (the campaign's GM's; rpg-ai, as a new speaker
        is saved)."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import ensure_person  # type: ignore[import-not-found]

        return ensure_person(model_registry, requester_id, campaign_id, name, summary).model_dump(mode="json")

    @classmethod
    @ability("learn_fact")
    def learn_fact(
        cls,
        model_registry: Any,
        requester_id: str,
        person_id: str,
        target_entity_type: str,
        target_entity_id: str,
        text: Optional[str] = None,
        learned_in: Optional[str] = None,
    ) -> dict[str, Any]:
        """``person_id`` (a player's character) learns ``text`` about a record, or with no text knows
        of it (which opens a record kept to the GM to them), learned in the session report
        ``learned_in``: {known_fact: {id, person_id, target_entity_type, target_entity_id, text,
        learned_in_journal_id, campaign_id, ...}, created}; the same fact twice is one row. The
        person's campaign's GM's to do (the AI GM, when a scene reveals something)."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import learn_fact  # type: ignore[import-not-found]

        return learn_fact(model_registry, requester_id, person_id, target_entity_type, target_entity_id, text, learned_in).model_dump(mode="json")

    @classmethod
    @ability("campaign_framing")
    def campaign_framing(cls, model_registry: Any, requester_id: str, campaign_id: str) -> dict[str, Any]:
        """A campaign's framing for the narrator: {"campaign_framing": {campaign_id, name,
        description, framing, gm_notes ("" for anyone but its GM), setting {id, name, tone} | null,
        play_styles, from_scenario}}; a playthrough with none of its own takes its scenario's."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import campaign_framing  # type: ignore[import-not-found]

        return {"campaign_framing": campaign_framing(model_registry, requester_id, campaign_id).model_dump(mode="json")}

    @classmethod
    @ability("remove_orphaned_records")
    def remove_orphaned_records(cls, model_registry: Any, requester_id: str, dry_run: bool = False) -> dict[str, Any]:
        """The requester's records whose campaign was deleted before deleting took them along,
        removed with their links, properties and pictures: {campaigns, removed: {type: count}}.
        dry_run counts what would go (the campaigns it treats as gone, and each type) and deletes
        nothing."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import remove_orphaned_records  # type: ignore[import-not-found]

        return remove_orphaned_records(model_registry, requester_id, dry_run=dry_run).model_dump(mode="json")

    @classmethod
    @ability("update_person")
    def update_person(cls, model_registry: Any, requester_id: str, person_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Fill in a person (an agent's NPC): fields from summary, entry (Markdown), personality,
        motive, voice, picture (an https link or an uploaded asset's id): {id, name, updated}."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import update_person  # type: ignore[import-not-found]

        return update_person(model_registry, requester_id, person_id, fields).model_dump(mode="json")

    @classmethod
    @ability("elevate_person")
    def elevate_person(cls, model_registry: Any, requester_id: str, person_id: str) -> dict[str, Any]:
        """A playthrough's person copied into its scenario (or linked to the one it has by name):
        {person_id, scenario_person_id, scenario_id, created}."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import elevate_person  # type: ignore[import-not-found]

        return elevate_person(model_registry, requester_id, person_id).model_dump(mode="json")

    @classmethod
    @ability("world_entities_matching")
    def world_entities_matching(
        cls, model_registry: Any, requester_id: str, campaign_id: str, text: str, limit: int = 50, include_setting: bool = True, tags: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Only the records the text names (name, alias or keyword, whole words, any case) plus the
        always-active, from the campaign and its setting's canon, through the key index:
        {world_entities: [...], matched: {id: [keys]}}. The narrator's relevance read."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import world_entities_matching  # type: ignore[import-not-found]

        return world_entities_matching(model_registry, requester_id, campaign_id, text, limit, include_setting, tags).model_dump(mode="json")

    @classmethod
    @ability("import_card_person")
    def import_card_person(cls, model_registry: Any, requester_id: str, card: dict[str, Any]) -> dict[str, Any]:
        """A SillyTavern character card as an NPC of the requester's own "Characters" campaign, to chat
        with outside any scenario: {person_id, campaign_id}. The card's fields by the spec's names or
        first_message / example_messages; avatar an https link or an uploaded asset's id. Not found
        by name: each call makes a person."""
        from zephyrex.extensions.rpg_core.CardPerson import import_card_person  # type: ignore[import-not-found]

        return import_card_person(model_registry, requester_id, card).model_dump()

    @classmethod
    @ability("lore_search")
    def lore_search(
        cls,
        model_registry: Any,
        requester_id: str,
        campaign_id: str,
        text: str,
        k: int = 20,
        token_budget: int = 2000,
        kinds: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        include_setting: bool = True,
    ) -> dict[str, Any]:
        """The campaign's lore passages for a text, best first, to ``k`` and ``token_budget``: the
        records the text names first, then full-text, trigram and vector ranks fused (RRF).
        {passages: [{id, record_id, record_type, name, path, text, tokens, source, page, score,
        ranks}], methods: {exact, text, trigram, vector: used | basic | unavailable: why}}."""
        from zephyrex.extensions.rpg_core.LoreSearch import lore_search  # type: ignore[import-not-found]

        return lore_search(model_registry, requester_id, campaign_id, text, k, token_budget, kinds, tags, include_setting).model_dump(mode="json")

    @classmethod
    @ability("import_book")
    def import_book(
        cls,
        model_registry: Any,
        requester_id: str,
        setting_id: str,
        game_system_id: Optional[str],
        slug: str,
        title: str,
        pages: list[Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """A transcribed book's pages ([(page, blocks)]) as passages of its setting's canon for
        lore_search, replacing an earlier import of it: {passages}. In process only (book_import);
        the operator's instance alone holds book text."""
        from zephyrex.extensions.rpg_core.LoreSearch import import_book  # type: ignore[import-not-found]

        return {"passages": import_book(model_registry, requester_id, setting_id, game_system_id, slug, title, [(int(page), blocks) for page, blocks in pages], dry_run)}

    @classmethod
    @ability("rebuild_lore_chunks")
    def rebuild_lore_chunks(cls, model_registry: Any, requester_id: str) -> dict[str, Any]:
        """Cut the requester's records made before the lore index (rpg_core 017) into passages:
        {kind: records indexed}. Run once after 017; the hooks keep it current after."""
        from zephyrex.extensions.rpg_core.LoreSearch import rebuild_lore_chunks  # type: ignore[import-not-found]

        return rebuild_lore_chunks(model_registry, requester_id)

    @classmethod
    @ability("register_embedder")
    def register_embedder(cls, model_registry: Any, requester_id: str, embed: Any, model: str) -> dict[str, Any]:
        """The composing app's embedder (texts in, 768-wide vectors out; rpg-ai's "embed"-role
        endpoint, nomic-embed-text-v1.5 with no prefixes: the wiki adds "search_document: " and
        "search_query: "). Recorded on each passage as embedded_model."""
        from zephyrex.extensions.rpg_core.LoreSearch import register_embedder  # type: ignore[import-not-found]

        register_embedder(embed, model)
        return {"model": model}

    @classmethod
    def register_services(cls, model_registry: Any, requester_id: str) -> list[Any]:
        """The lore embedding loop (LoreSearch.LoreEmbeddingService): idle without an embedder or
        off Postgres."""
        from zephyrex.extensions.rpg_core.LoreSearch import LoreEmbeddingService  # type: ignore[import-not-found]

        return [LoreEmbeddingService(requester_id=requester_id, model_registry=model_registry)]

    @classmethod
    @ability("rebuild_world_keys")
    def rebuild_world_keys(cls, model_registry: Any, requester_id: str) -> dict[str, Any]:
        """Index the requester's records made before the key index existed: {kind: records indexed}.
        Run once after rpg_core 016; the hooks keep it current after."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import rebuild_world_keys  # type: ignore[import-not-found]

        return rebuild_world_keys(model_registry, requester_id)

    @classmethod
    @ability("campaign_documents")
    def campaign_documents(cls, model_registry: Any, requester_id: str, campaign_id: str) -> dict[str, Any]:
        """Each of the campaign's records' full text, journals first: {"campaign_documents": [{id, kind,
        name, text, gm_only}]} (Parity's data bank)."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import campaign_documents  # type: ignore[import-not-found]

        return campaign_documents(model_registry, requester_id, campaign_id).model_dump(mode="json")

