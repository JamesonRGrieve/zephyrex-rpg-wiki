# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core models: the same resources, fields and rules as the lite edition's
(client/src/lib/campaignRecords.ts, personRecords.ts).

- ``/v1/campaign``: a world. Its owner is ``user_id``.
- ``/v1/person`` (genealogy's) gains ``kind`` (contract/wiki.json person_kinds), ``campaign_id``,
  ``user_id`` (the player; none for an NPC), ``location_id`` (where they are) and ``entry`` (a Plate
  value, its plain text kept as the description).
- ``/v1/location`` (world_spatial's) and ``/v1/faction`` (world_social's) gain ``campaign_id``.
- ``/v1/item`` (world_inventory's) and ``/v1/journal`` (world_narrative's) gain ``campaign_id``.
- ``/v1/world_entity`` (rpg-ai A15): a campaign's places, people, factions, items and journals changed
  since a time, tombstones included, paged; the same logic as the ``world_entities`` ability.
- ``/v1/session_report`` (rpg-ai A24): write a session report into a campaign as a journal, and read
  one back; the same logic as the ``session_report`` abilities (EXT_RPGCore.py).

Rule systems (game_systems, and game_system_id on campaigns and items) are zephyrex-vtt's
rpg_systems (operator, 2026-11-20): the wiki depends on no other suite product.

Each ``*_id`` names its model, so the framework gives it a real foreign key.
"""

import json
from datetime import datetime
from typing import Any, Callable, ClassVar, Optional, Type

from fastapi import HTTPException
from pydantic import BaseModel as PlainModel
from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.genealogy.BLL_Genealogy import PersonManager, PersonModel
from zephyrex.lib.Rooms import room_of
from zephyrex.extensions.wiki_shared.Contract import PERSON_KINDS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import (  # type: ignore[import-not-found]
    checked_kind,
    checked_name,
    checked_slug,
    free_slug,
    slugify,
    with_entry_text,
)
from zephyrex.extensions.wiki_shared.EntityIds import EntityIdsError, entity_ids  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Lore import lore_text, stored_lore  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Pictures import picture_url as checked_picture_url  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Provenance import HOMEBREW, checked_provenance, checked_source, provenance  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Names import names_text, stored_names, stored_voice, tts_voice_text, voice_text  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Routine import (  # type: ignore[import-not-found]
    clock,
    motivations_text,
    routine_text,
    stored_motivations,
    stored_routine,
)
from zephyrex.extensions.wiki_shared.Contract import ATTACHMENT_ROLES, CANON_LEVELS, DOCUMENT_KINDS, ENTITY_TYPES, GM_ONLY_PROPERTY, LIMITS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Documents import ordered_documents  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Report import report_entry  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Summary import summary  # type: ignore[import-not-found]
from zephyrex.extensions.world_inventory.BLL_WorldInventory import (  # type: ignore[import-not-found]
    EntityInventoryManager,
    ItemInstanceManager,
    ItemManager,
    ItemModel,
)
from zephyrex.extensions.world_narrative.BLL_WorldNarrative import (  # type: ignore[import-not-found]
    HookDependencyManager,
    HookManager,
    HookModel,
    JournalManager,
    JournalModel,
    requirement_of,
)
from zephyrex.extensions.wiki_shared.Requirements import hook_state  # type: ignore[import-not-found]
from zephyrex.extensions.world_taxonomy.BLL_WorldTaxonomy import (  # type: ignore[import-not-found]
    EntityTaxonManager,
    StatusManager,
    StatusModel,
    TaxonManager,
    TaxonModel,
)
from zephyrex.extensions.world_properties.BLL_WorldProperties import PropertyKitManager, PropertyKitModel  # type: ignore[import-not-found]
from zephyrex.extensions.world_social.BLL_WorldSocial import FactionManager, FactionModel  # type: ignore[import-not-found]
from zephyrex.extensions.world_spatial.BLL_WorldSpatial import LocationManager, LocationModel  # type: ignore[import-not-found]
from zephyrex.logic.AbstractLogicManager import (
    AbstractBLLManager,
    ApplicationModel,
    BooleanSearchModel,
    DescriptionMixinModel,
    HookContext,
    HookTiming,
    ModelMeta,
    NameMixinModel,
    StringSearchModel,
    UpdateMixinModel,
    hook_bll,
)
from zephyrex.lib.CustomRoute import ExposeIn, custom_route
from zephyrex.lib.Environment import env
from zephyrex.logic.BLL_Auth import UserModel
from zephyrex.pydantic2.fastapi import RouterMixin
from zephyrex.pydantic2.fastapi.types import RouteType

# The framework's registry BaseModel, which it re-exports without declaring it.
from zephyrex.pydantic2.registry import BaseModel  # type: ignore[attr-defined]
from zephyrex.pydantic2.sqlalchemy import extension_model


class SettingModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    metaclass=ModelMeta,
):
    """A setting (S6; rpg-ai DESIGN "Settings and systems", the operator, 2026-11-21): the universe
    its campaigns take place in (Warhammer 40,000, Fantasy, Fallout, Modern…). Its canon is every
    world record with this setting and no campaign: what anyone in it would know. VTT's game systems
    name the settings they play in."""

    Manager: ClassVar[Type["SettingManager"]] = None
    entry: Optional[str] = Field(None, description="Its tone and vocabulary: a Plate value as JSON text")
    slug: Optional[str] = Field(
        None, description="Its stable name (contract/wiki.json setting_slug): unique, fixed once set; vtt's systems name it"
    )
    table_comment: ClassVar[str] = "A setting: the universe campaigns take place in; its canon is its campaign-less records."

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        entry: Optional[Any] = None
        slug: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _slug = field_validator("slug")(checked_slug)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        entry: Optional[Any] = None
        # Only to say it stays: a different slug is refused (_slug_fixed).
        slug: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _slug = field_validator("slug")(checked_slug)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Search(ApplicationModel.Search):
        name: Optional[StringSearchModel] = None
        slug: Optional[StringSearchModel] = None


class SettingPregen(PlainModel):
    id: str
    name: str
    summary: str = Field(..., description="Its one line: the first line of its entry")
    picture_url: Optional[str] = None
    tags: list[str] = Field(..., description="Its tags' names: Pregen, its class or role, …")
    source: Optional[str] = None


class SettingPregens(PlainModel):
    pregens: list[SettingPregen]


class SettingManager(AbstractBLLManager, RouterMixin):
    _model = SettingModel

    @custom_route(
        method="GET",
        path="/{id}/pregen",
        output_model=SettingPregens,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Settings",),
        summary="The setting's pregenerated player characters, to pick from at a start (canon pcs tagged Pregen)",
    )
    def pregen_route(self, id: str) -> SettingPregens:
        return setting_pregens(self.model_registry, str(self.requester.id), id)


def _slug_taken(manager: Any, slug: str) -> bool:
    """Any setting holds the slug, anyone's and deleted ones too (ROOT sees them all), as the unique
    index counts them."""
    root = SettingManager(requester_id=env("ROOT_ID"), model_registry=manager.model_registry)
    return bool(root.list(slug=slug))


def _slug_fixed(context: HookContext) -> None:
    """S6b: a setting's slug is the one given (409 when another setting holds it) or its name's
    (numbered past any taken), and is fixed once set."""
    if context.method_name == "create":
        given = checked_slug(context.kwarg("slug", default=None))
        if given is not None:
            if _slug_taken(context.manager, given):
                raise HTTPException(status_code=409, detail="Another setting already has that slug")
            return
        slug = slugify(str(context.kwarg("name", default="") or ""))
        taken = set()
        while (candidate := free_slug(slug, taken)) and _slug_taken(context.manager, candidate):
            taken.add(candidate)
        context.kwargs["slug"] = candidate
        return
    if context.method_name != "update":
        return
    wanted = context.kwarg("slug", default=None)
    if wanted is None:
        return
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    try:
        held = getattr(context.manager.get(id=record_id), "slug", None) if record_id else None
    except HTTPException:
        return
    if wanted != held:
        raise HTTPException(status_code=422, detail="A setting's slug is fixed once set")


hook_bll(SettingManager, timing=HookTiming.BEFORE, priority=21)(_slug_fixed)


SettingModel.Manager = SettingManager


class CampaignModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    UserModel.Reference.Optional,
    SettingModel.Reference.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["CampaignManager"]] = None
    table_comment: ClassVar[str] = "A world: the top-level container every record scopes to. user_id = its owner."

    # Where the scenario came from (operator, 2026-11-21: official ones are parsed in for personal use).
    provenance: Optional[str] = Field(None, description="contract/wiki.json provenances: homebrew, official or adapted")
    source: Optional[str] = Field(None, description="The official title, publisher and product or page; none for homebrew")
    # Copy on start (operator, 2026-11-21): a scenario is never played; starting it makes a playthrough.
    is_scenario: Optional[bool] = Field(None, description="A scenario: play never edits it; starting it copies it (instantiate)")
    scenario_id: Optional[str] = Field(None, description="FK → campaigns.id; the scenario this campaign is a playthrough of")
    clock_minutes: Optional[int] = Field(None, description="In-world time: minutes from day 1, 00:00; none = day 1, 08:00 (advance_clock)")

    class Create(BaseModel, UserModel.Reference.ID.Optional, SettingModel.Reference.ID.Optional):
        name: str = Field(...)
        description: Optional[str] = None
        provenance: Optional[str] = None
        source: Optional[str] = None
        is_scenario: Optional[bool] = None
        scenario_id: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        _source = field_validator("source")(checked_source)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        setting_id: Optional[str] = None
        is_scenario: Optional[bool] = None
        provenance: Optional[str] = None
        # "" clears it; none leaves it as it is (read by _provenance_holds).
        source: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))

    class Search(ApplicationModel.Search, UserModel.Reference.ID.Search, SettingModel.Reference.ID.Search):
        name: Optional[StringSearchModel] = None


class CampaignStart(PlainModel):
    name: Optional[str] = Field(None, description="The playthrough's name; the scenario's when not given")
    pregens: Optional[list[str]] = Field(None, description="The setting's pregens (person ids) the party picked: each copied into the playthrough")


class CampaignStartEnvelope(PlainModel):
    instantiate: CampaignStart


class CampaignStartModel(ApplicationModel.Optional, UpdateMixinModel.Optional, metaclass=ModelMeta):
    """A scenario being started in the background (operator, 2026-11-21: "make it async with the
    progress bar and auto load it when it's done"): its state, its progress through START_STEPS,
    and, when done, the playthrough and its id map; when failed, why (nothing is left behind)."""

    Manager: ClassVar[Type["CampaignStartManager"]] = None
    table_comment: ClassVar[str] = "A scenario being started in the background: state, progress, and the playthrough."

    scenario_id: Optional[str] = Field(None, description="FK → campaigns.id; the scenario being started")
    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; the playthrough, once made")
    name: Optional[str] = Field(None, description="The playthrough's name as asked for")
    state: Optional[str] = Field(None, description="running, done or failed")
    done: Optional[int] = Field(None, description="Steps finished")
    total: Optional[int] = Field(None, description="Steps in all")
    step: Optional[str] = Field(None, description="The step under way (copying people, …)")
    id_map: Optional[str] = Field(None, description="When done: each copied id → its copy's, as JSON text")
    error: Optional[str] = Field(None, description="When failed: why")

    class Create(BaseModel):
        scenario_id: str = Field(...)
        name: Optional[str] = None
        state: Optional[str] = None
        done: Optional[int] = None
        total: Optional[int] = None
        step: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None
        state: Optional[str] = None
        done: Optional[int] = None
        step: Optional[str] = None
        id_map: Optional[str] = None
        error: Optional[str] = None

    class Search(ApplicationModel.Search):
        pass


class CampaignStartAccepted(PlainModel):
    start: dict[str, Any] = Field(..., description="The start: id, scenario_id, state running, done 0, total")


class CampaignStartOne(PlainModel):
    campaign_start: dict[str, Any] = Field(..., description="The start: state, done, total, step; campaign_id and id_map when done; error when failed")


class CampaignStartManager(AbstractBLLManager, RouterMixin):
    """GET /v1/campaign_start/{id}: one's own start, as the copy runs; its list. Made only by POST
    /v1/campaign/{id}/instantiate."""

    _model = CampaignStartModel
    routes_to_register: ClassVar[list[RouteType] | None] = [RouteType.LIST]

    @custom_route(
        method="GET",
        path="/{id}",
        output_model=CampaignStartOne,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="A start's progress, to the one who started it",
    )
    def progress_route(self, id: str) -> CampaignStartOne:
        # Polled while the copy runs in this process: one row by id, read as SYSTEM and checked
        # against its starter, so a poll costs little beside the copy (a permission-filtered read
        # each half second slowed a 120-record start from 8 s to 50 s on the runner).
        row = CampaignStartManager(requester_id=env("SYSTEM_ID"), model_registry=self.model_registry).get(id=id)
        if str(getattr(row, "created_by_user_id", "") or "") != str(self.requester.id):
            raise HTTPException(status_code=404, detail="CampaignStartModel not found")
        return CampaignStartOne(campaign_start=row.model_dump(mode="json"))


CampaignStartModel.Manager = CampaignStartManager


class CampaignStarted(PlainModel):
    campaign: dict[str, Any] = Field(..., description="The new campaign, a playthrough of the scenario")
    id_map: dict[str, str] = Field(..., description="Each copied record's id (and the scenario's) → its copy's")


class PersonEnsure(PlainModel):
    name: str = Field(..., description="Who they are, as the narrator named them (The Barkeep)")
    summary: Optional[str] = Field(None, description="One line on them, their entry")


class PersonEnsureEnvelope(PlainModel):
    person: PersonEnsure


class PersonFill(PlainModel):
    person_id: str
    summary: Optional[str] = Field(None, description="One line on them: the entry's first paragraph")
    entry: Optional[str] = Field(None, description="Their description, as Markdown (headings, lists, paragraphs)")
    personality: Optional[str] = Field(None, description="Their voice's personality")
    motive: Optional[str] = Field(None, description="What drives them: added to their motivations")
    voice: Optional[str] = Field(None, description="How they speak: their voice's speech")
    tts_voice: Optional[str] = Field(None, description="The TTS model's voice id for their lines; \"\" back to the default")
    picture: Optional[str] = Field(None, description="An https link (picture_url), or an uploaded asset's id (attached as their picture)")


class PersonFillEnvelope(PlainModel):
    person: PersonFill


class PersonFilled(PlainModel):
    id: str
    name: str
    updated: list[str] = Field(..., description="The fields that changed")


class PersonFilledOne(PlainModel):
    person: PersonFilled


class ElevateAsk(PlainModel):
    person_id: str


class ElevateEnvelope(PlainModel):
    elevate: ElevateAsk


class PersonElevated(PlainModel):
    person_id: str = Field(..., description="The campaign's person")
    scenario_person_id: str = Field(..., description="Their scenario counterpart")
    scenario_id: str
    created: bool = Field(..., description="Made now (false: the scenario already had them)")


class PersonElevatedOne(PlainModel):
    elevated: PersonElevated


class MatchingAsk(PlainModel):
    text: str = Field(..., description="The story text to match (recent turns)")
    limit: int = Field(50, description="At most this many records (1 to 100)")
    include_setting: bool = Field(True, description="Its setting's canon too")
    tags: Optional[list[str]] = Field(None, description="Only records tagged with any of these")


class MatchingEnvelope(PlainModel):
    matching: MatchingAsk


class PersonEnsured(PlainModel):
    id: str
    name: str
    created: bool = Field(..., description="Made now (false: the campaign already had them)")


class PersonEnsuredOne(PlainModel):
    person: PersonEnsured


class FramingSetting(PlainModel):
    id: str
    name: str
    tone: str = Field(..., description="The setting's entry as plain text: its tone and vocabulary")


class CampaignFraming(PlainModel):
    campaign_id: str
    name: str
    description: str = Field(..., description="The campaign's public description")
    framing: str = Field(..., description="Its framing journal's public text, by section")
    gm_notes: str = Field(..., description="Its framing's GM part (GM sections, or a GM-only framing); \"\" for anyone but its GM")
    setting: Optional[FramingSetting] = None
    play_styles: list[str]
    from_scenario: bool = Field(..., description="Its own were empty, so these are its scenario's")


class CampaignFramingOne(PlainModel):
    campaign_framing: CampaignFraming


class CampaignClock(PlainModel):
    minutes: int = Field(..., description="In-world minutes from day 1, 00:00")
    day: int = Field(..., description="The in-world day, from 1")
    time: str = Field(..., description="The in-world time of day, HH:MM")
    reason: Optional[str] = Field(None, description="Why it was advanced, when it just was")


class ClockAdvance(PlainModel):
    minutes: int = Field(..., description="How far to advance it, in minutes (at least 1)")
    reason: Optional[str] = None


class ClockAdvanceEnvelope(PlainModel):
    clock: ClockAdvance


class CampaignManager(AbstractBLLManager, RouterMixin):
    _model = CampaignModel

    @custom_route(
        method="POST",
        path="/{id}/instantiate",
        input_model=CampaignStartEnvelope,
        output_model=CampaignStartAccepted,
        authentication_type="jwt",
        status_code=202,
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="Start a scenario in the background: a new campaign with its own copy of every record and relation (GET /v1/campaign_start/{id} for progress)",
    )
    def instantiate_route(self, id: str, instantiate: CampaignStart) -> CampaignStartAccepted:
        start = CampaignStart.model_validate(instantiate)
        return start_campaign(self.model_registry, str(self.requester.id), id, start.name, start.pregens or [])

    @custom_route(
        method="POST",
        path="/{id}/person",
        input_model=PersonEnsureEnvelope,
        output_model=PersonEnsuredOne,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="A person of the campaign by name, made (GM only, made in play) when it has none: the campaign's GM's",
    )
    def ensure_person_route(self, id: str, person: PersonEnsure) -> PersonEnsuredOne:
        asked = PersonEnsure.model_validate(person)
        return PersonEnsuredOne(person=ensure_person(self.model_registry, str(self.requester.id), id, asked.name, asked.summary))

    @custom_route(
        method="POST",
        path="/{id}/fill_person",
        input_model=PersonFillEnvelope,
        output_model=PersonFilledOne,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="Fill in a campaign's person (an agent's NPC): one line, a Markdown description, personality, motive, voice, picture",
    )
    def fill_person_route(self, id: str, person: PersonFill) -> PersonFilledOne:
        asked = PersonFill.model_validate(person)
        filled = update_person(self.model_registry, str(self.requester.id), asked.person_id, asked.model_dump(exclude={"person_id"}, exclude_none=True), campaign_id=id)
        return PersonFilledOne(person=filled)

    @custom_route(
        method="POST",
        path="/{id}/elevate",
        input_model=ElevateEnvelope,
        output_model=PersonElevatedOne,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="Elevate a playthrough's person to its scenario, so later playthroughs have them (its GM's)",
    )
    def elevate_route(self, id: str, elevate: ElevateAsk) -> PersonElevatedOne:
        asked = ElevateAsk.model_validate(elevate)
        return PersonElevatedOne(elevated=elevate_person(self.model_registry, str(self.requester.id), asked.person_id, campaign_id=id))

    @custom_route(
        method="GET",
        path="/{id}/framing",
        output_model=CampaignFramingOne,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="A campaign's framing for the narrator: description, framing, GM notes (its GM only), setting, play styles",
    )
    def framing_route(self, id: str) -> CampaignFramingOne:
        return CampaignFramingOne(campaign_framing=campaign_framing(self.model_registry, str(self.requester.id), id))

    @custom_route(
        method="GET",
        path="/{id}/clock",
        output_model=CampaignClock,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="The campaign's in-world clock (day 1, 08:00 until play advances it)",
    )
    def clock_route(self, id: str) -> CampaignClock:
        return campaign_clock(self.model_registry, str(self.requester.id), id)

    @custom_route(
        method="POST",
        path="/{id}/clock",
        input_model=ClockAdvanceEnvelope,
        output_model=CampaignClock,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="Advance the campaign's in-world clock (its GM: EDIT on the campaign)",
    )
    def advance_route(self, id: str, clock: ClockAdvance) -> CampaignClock:
        advance = ClockAdvance.model_validate(clock)
        return advance_clock(self.model_registry, str(self.requester.id), id, advance.minutes, advance.reason)


def _provenance_holds(context: HookContext) -> None:
    """A campaign's (or a record's) provenance and source checked together: on create, homebrew when
    not given; on update, against what it holds (homebrew has no source, so making one homebrew
    clears its source)."""
    if context.method_name == "create":
        given = {"provenance": context.kwarg("provenance", default=None), "source": context.kwarg("source", default=None)}
    elif context.method_name == "update":
        # None is "not given": the provenance can't be emptied, and "" clears the source.
        wanted = {key: _UNSET if (value := context.kwarg(key, default=_UNSET)) is None else value for key in ("provenance", "source")}
        if all(value is _UNSET for value in wanted.values()):
            return
        record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
        try:
            held = context.manager.get(id=record_id) if record_id else None
        except HTTPException:
            return
        given = {key: getattr(held, key, None) if value is _UNSET else value for key, value in wanted.items()}
        if wanted["provenance"] == HOMEBREW and wanted["source"] is _UNSET:
            given["source"] = None
    else:
        return
    try:
        checked = provenance(given)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    context.kwargs.update(checked)


hook_bll(CampaignManager, timing=HookTiming.BEFORE, priority=20)(_provenance_holds)


CampaignModel.Manager = CampaignManager


def _person_kind(value: Any) -> Any:
    return checked_kind(value, PERSON_KINDS, "person")


@extension_model(PersonModel)
class RPG_PersonModel(BaseModel):
    """genealogy's Person as the character table: kind, campaign, player, place and entry."""

    kind: Optional[str] = Field(None, description="contract/wiki.json person_kinds")
    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = campaign-free, or with a setting its canon")
    setting_id: Optional[str] = Field(None, description="FK → settings.id; with no campaign, the setting\'s canon (S6)")
    canon_level: Optional[str] = Field(None, description="contract/wiki.json canon_levels; unset until decided")
    is_template: Optional[bool] = Field(None, description="A template (W7): copied into campaigns, never a world fact")
    aliases: Optional[str] = Field(None, description="Other names it goes by, as JSON text (S4c)")
    keywords: Optional[str] = Field(None, description="What else wakes it in the AI's lorebook, as JSON text (S4c)")
    lore: Optional[str] = Field(None, description="Its lorebook activation (SillyTavern World Info's fields), as JSON text (S4d)")
    provenance: Optional[str] = Field(None, description="contract/wiki.json provenances: homebrew, official or adapted")
    source: Optional[str] = Field(None, description="The official title, publisher and product or page; none for homebrew")
    picture_url: Optional[str] = Field(None, description="Its picture by https link (fandom, wikis…), shown before an uploaded one")
    voice: Optional[str] = Field(None, description="How the AI plays them: personality, speech, first_message, examples, as JSON text (S4c; GM-facing)")
    # Operator, 2026-11-23: "A voice per character": the TTS model's voice their lines are read in.
    tts_voice: Optional[str] = Field(None, description="The TTS model's voice id for their lines (alloy, onyx…); none is the default")
    # The world tick (operator, 2026-11-21): the GM side pilots each person by these as time advances.
    routine: Optional[str] = Field(None, description="Their schedule: slots {from, to, days, location_id, activity}, as JSON text (GM-facing)")
    motivations: Optional[str] = Field(None, description="Their goals, fears and current intent, a list as JSON text (GM-facing)")
    user_id: Optional[str] = Field(None, description="FK → users.id; the player. None = an NPC")
    location_id: Optional[str] = Field(None, description="FK → locations.id; where they are")
    entry: Optional[str] = Field(None, description="The entry: a Plate value as JSON text")

    class Create(BaseModel):
        kind: Optional[str] = None
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        _source = field_validator("source")(checked_source)
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(checked_picture_url)
        voice: Optional[Any] = None
        _voice = field_validator("voice")(voice_text)
        tts_voice: Optional[str] = None
        _tts_voice = field_validator("tts_voice")(tts_voice_text)
        routine: Optional[Any] = None
        _routine = field_validator("routine")(routine_text)
        motivations: Optional[Any] = None
        _motivations = field_validator("motivations")(motivations_text)
        user_id: Optional[str] = None
        location_id: Optional[str] = None
        entry: Optional[Any] = None

        _kind = field_validator("kind")(_person_kind)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Update(BaseModel):
        kind: Optional[str] = None
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        # "" clears it (none leaves it as it is).
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(lambda value: value if value is None else (checked_picture_url(value) or ""))
        voice: Optional[Any] = None
        _voice = field_validator("voice")(voice_text)
        # "" clears it back to the default (none leaves it as it is).
        tts_voice: Optional[str] = None
        _tts_voice = field_validator("tts_voice")(lambda value: value if value is None else (tts_voice_text(value) or ""))
        routine: Optional[Any] = None
        _routine = field_validator("routine")(routine_text)
        motivations: Optional[Any] = None
        _motivations = field_validator("motivations")(motivations_text)
        user_id: Optional[str] = None
        location_id: Optional[str] = None
        entry: Optional[Any] = None

        _kind = field_validator("kind")(_person_kind)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Search(BaseModel):
        kind: Optional[StringSearchModel] = None
        campaign_id: Optional[StringSearchModel] = None
        setting_id: Optional[StringSearchModel] = None
        canon_level: Optional[StringSearchModel] = None
        is_template: Optional[BooleanSearchModel] = None
        user_id: Optional[StringSearchModel] = None
        location_id: Optional[StringSearchModel] = None


@extension_model(LocationModel)
class RPG_LocationModel(BaseModel):
    """A location's campaign: rpg_core scopes Tier 1 records, never the reverse."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")
    setting_id: Optional[str] = Field(None, description="FK → settings.id; with no campaign, the setting\'s canon (S6)")
    canon_level: Optional[str] = Field(None, description="contract/wiki.json canon_levels; unset until decided")
    is_template: Optional[bool] = Field(None, description="A template (W7): copied into campaigns, never a world fact")
    aliases: Optional[str] = Field(None, description="Other names it goes by, as JSON text (S4c)")
    keywords: Optional[str] = Field(None, description="What else wakes it in the AI's lorebook, as JSON text (S4c)")
    lore: Optional[str] = Field(None, description="Its lorebook activation (SillyTavern World Info's fields), as JSON text (S4d)")
    provenance: Optional[str] = Field(None, description="contract/wiki.json provenances: homebrew, official or adapted")
    source: Optional[str] = Field(None, description="The official title, publisher and product or page; none for homebrew")
    picture_url: Optional[str] = Field(None, description="Its picture by https link (fandom, wikis…), shown before an uploaded one")

    class Create(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        _source = field_validator("source")(checked_source)
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(checked_picture_url)

    class Update(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        # "" clears it (none leaves it as it is).
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(lambda value: value if value is None else (checked_picture_url(value) or ""))

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None
        setting_id: Optional[StringSearchModel] = None
        canon_level: Optional[StringSearchModel] = None
        is_template: Optional[BooleanSearchModel] = None


@extension_model(FactionModel)
class RPG_FactionModel(BaseModel):
    """A faction's campaign: rpg_core scopes Tier 1 records, never the reverse."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")
    setting_id: Optional[str] = Field(None, description="FK → settings.id; with no campaign, the setting\'s canon (S6)")
    canon_level: Optional[str] = Field(None, description="contract/wiki.json canon_levels; unset until decided")
    is_template: Optional[bool] = Field(None, description="A template (W7): copied into campaigns, never a world fact")
    aliases: Optional[str] = Field(None, description="Other names it goes by, as JSON text (S4c)")
    keywords: Optional[str] = Field(None, description="What else wakes it in the AI's lorebook, as JSON text (S4c)")
    lore: Optional[str] = Field(None, description="Its lorebook activation (SillyTavern World Info's fields), as JSON text (S4d)")
    provenance: Optional[str] = Field(None, description="contract/wiki.json provenances: homebrew, official or adapted")
    source: Optional[str] = Field(None, description="The official title, publisher and product or page; none for homebrew")
    picture_url: Optional[str] = Field(None, description="Its picture by https link (fandom, wikis…), shown before an uploaded one")

    class Create(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        _source = field_validator("source")(checked_source)
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(checked_picture_url)

    class Update(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        # "" clears it (none leaves it as it is).
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(lambda value: value if value is None else (checked_picture_url(value) or ""))

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None
        setting_id: Optional[StringSearchModel] = None
        canon_level: Optional[StringSearchModel] = None
        is_template: Optional[BooleanSearchModel] = None


@extension_model(ItemModel)
class RPG_ItemModel(BaseModel):
    """An item's campaign: rpg_core scopes Tier 1 records, never the reverse. Its rule system is
    zephyrex-vtt's rpg_systems' to add (game_systems moved there; operator, 2026-11-20)."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")
    setting_id: Optional[str] = Field(None, description="FK → settings.id; with no campaign, the setting\'s canon (S6)")
    canon_level: Optional[str] = Field(None, description="contract/wiki.json canon_levels; unset until decided")
    is_template: Optional[bool] = Field(None, description="A template (W7): copied into campaigns, never a world fact")
    aliases: Optional[str] = Field(None, description="Other names it goes by, as JSON text (S4c)")
    keywords: Optional[str] = Field(None, description="What else wakes it in the AI's lorebook, as JSON text (S4c)")
    lore: Optional[str] = Field(None, description="Its lorebook activation (SillyTavern World Info's fields), as JSON text (S4d)")
    provenance: Optional[str] = Field(None, description="contract/wiki.json provenances: homebrew, official or adapted")
    source: Optional[str] = Field(None, description="The official title, publisher and product or page; none for homebrew")
    picture_url: Optional[str] = Field(None, description="Its picture by https link (fandom, wikis…), shown before an uploaded one")

    class Create(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        _source = field_validator("source")(checked_source)
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(checked_picture_url)

    class Update(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        # "" clears it (none leaves it as it is).
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(lambda value: value if value is None else (checked_picture_url(value) or ""))

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None
        setting_id: Optional[StringSearchModel] = None
        canon_level: Optional[StringSearchModel] = None
        is_template: Optional[BooleanSearchModel] = None


# ---------------------------------------------------------------------------
# A record's world is fixed once set (Zephyrex RPG, for rpg-ai's A15 sync)
# ---------------------------------------------------------------------------
#
# A since-sync reads a world's changes; a record that left a world would vanish from it without a
# tombstone. So campaign_id goes from none to a world, never from a world to another or back to
# none: moving is copy and delete, which leaves the tombstone. The lite edition refuses the same.

_UNSET = object()


def _world_stays(context: HookContext) -> None:
    if context.method_name != "update":
        return
    wanted = context.kwarg("campaign_id", default=_UNSET)
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if wanted is _UNSET or not record_id:
        return
    try:
        current = getattr(context.manager.get(id=record_id), "campaign_id", None)
    except HTTPException:
        return
    if current is not None and wanted != current:
        raise HTTPException(status_code=422, detail="A record's world is fixed once set: copy it to another world instead")


for _manager in (PersonManager, LocationManager, FactionManager, ItemManager, JournalManager, HookManager, TaxonManager, StatusManager, PropertyKitManager):
    hook_bll(_manager, timing=HookTiming.BEFORE, priority=20)(_world_stays)

# Where a record came from, as a campaign says it (operator, 2026-11-21: entities have provenance too).
for _manager in (PersonManager, LocationManager, FactionManager, ItemManager, JournalManager, HookManager):
    hook_bll(_manager, timing=HookTiming.BEFORE, priority=22)(_provenance_holds)


def _template_stays(context: HookContext) -> None:
    """S4b: a record is a template or not from its creation. A record that became one would leave the
    world sync without a tombstone, so making a template is a copy (template/instantiate)."""
    if context.method_name != "update":
        return
    wanted = context.kwarg("is_template", default=_UNSET)
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if wanted is _UNSET or wanted is None or not record_id:
        return
    try:
        current = bool(getattr(context.manager.get(id=record_id), "is_template", None))
    except HTTPException:
        return
    if bool(wanted) != current:
        raise HTTPException(status_code=422, detail="A record is a template or not from its creation: copy it instead")


for _manager in (PersonManager, LocationManager, FactionManager, ItemManager, JournalManager, HookManager):
    hook_bll(_manager, timing=HookTiming.BEFORE, priority=20)(_template_stays)


def _setting_fits(context: HookContext) -> None:
    """S6: a record's setting is one of the caller's, fixed once set, and the same as its campaign's
    (a campaign record belongs to its campaign's setting); a canon level is from the contract."""
    if context.method_name not in ("create", "update"):
        return
    level = context.kwarg("canon_level", default=None)
    if level is not None and level not in CANON_LEVELS:
        raise HTTPException(status_code=422, detail=f"A canon level is one of: {', '.join(CANON_LEVELS)}")
    wanted_setting = context.kwarg("setting_id", default=_UNSET)
    wanted_campaign = context.kwarg("campaign_id", default=_UNSET)
    current = None
    if context.method_name == "update":
        record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
        try:
            current = context.manager.get(id=record_id) if record_id else None
        except HTTPException:
            return
        held = getattr(current, "setting_id", None)
        if held is not None and wanted_setting is not _UNSET and wanted_setting != held:
            raise HTTPException(status_code=422, detail="A record's setting is fixed once set: copy it to another setting instead")
    setting = wanted_setting if wanted_setting is not _UNSET else getattr(current, "setting_id", None)
    campaign = wanted_campaign if wanted_campaign is not _UNSET else getattr(current, "campaign_id", None)
    registry, requester = context.manager.model_registry, str(context.manager.requester.id)
    if setting:
        try:
            _manager(registry, requester, SettingManager).get(id=setting)
        except HTTPException as error:
            raise HTTPException(status_code=422, detail="That setting is not one of yours") from error
    if setting and campaign:
        try:
            enclosing = getattr(_manager(registry, requester, CampaignManager).get(id=campaign), "setting_id", None)
        except HTTPException:
            return
        if enclosing != setting:
            raise HTTPException(status_code=422, detail="A campaign's record belongs to its campaign's setting")


def _campaign_setting_stays(context: HookContext) -> None:
    """A campaign's setting is one of the caller's, and fixed once set, as a record's world is."""
    if context.method_name not in ("create", "update"):
        return
    wanted = context.kwarg("setting_id", default=_UNSET)
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if context.method_name == "create":
        wanted = context.kwarg("setting_id", default=None)
        if wanted:
            try:
                _manager(context.manager.model_registry, str(context.manager.requester.id), SettingManager).get(id=wanted)
            except HTTPException as error:
                raise HTTPException(status_code=422, detail="That setting is not one of yours") from error
        return
    if wanted is _UNSET or not record_id:
        return
    try:
        held = getattr(context.manager.get(id=record_id), "setting_id", None)
    except HTTPException:
        return
    if held is not None and wanted != held:
        raise HTTPException(status_code=422, detail="A campaign's setting is fixed once set")
    if wanted:
        try:
            _manager(context.manager.model_registry, str(context.manager.requester.id), SettingManager).get(id=wanted)
        except HTTPException as error:
            raise HTTPException(status_code=422, detail="That setting is not one of yours") from error


for _owner in (PersonManager, LocationManager, FactionManager, ItemManager, JournalManager, HookManager, TaxonManager, StatusManager, PropertyKitManager):
    hook_bll(_owner, timing=HookTiming.BEFORE, priority=21)(_setting_fits)
hook_bll(CampaignManager, timing=HookTiming.BEFORE, priority=21)(_campaign_setting_stays)



@extension_model(JournalModel)
class RPG_JournalModel(BaseModel):
    """A journal's campaign: rpg_core scopes Tier 1 records, never the reverse."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")
    setting_id: Optional[str] = Field(None, description="FK → settings.id; with no campaign, the setting\'s canon (S6)")
    canon_level: Optional[str] = Field(None, description="contract/wiki.json canon_levels; unset until decided")
    is_template: Optional[bool] = Field(None, description="A template (W7): copied into campaigns, never a world fact")
    aliases: Optional[str] = Field(None, description="Other names it goes by, as JSON text (S4c)")
    keywords: Optional[str] = Field(None, description="What else wakes it in the AI's lorebook, as JSON text (S4c)")
    lore: Optional[str] = Field(None, description="Its lorebook activation (SillyTavern World Info's fields), as JSON text (S4d)")
    provenance: Optional[str] = Field(None, description="contract/wiki.json provenances: homebrew, official or adapted")
    source: Optional[str] = Field(None, description="The official title, publisher and product or page; none for homebrew")
    picture_url: Optional[str] = Field(None, description="Its picture by https link (fandom, wikis…), shown before an uploaded one")

    class Create(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        _source = field_validator("source")(checked_source)
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(checked_picture_url)

    class Update(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        # "" clears it (none leaves it as it is).
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(lambda value: value if value is None else (checked_picture_url(value) or ""))

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None
        setting_id: Optional[StringSearchModel] = None
        canon_level: Optional[StringSearchModel] = None
        is_template: Optional[BooleanSearchModel] = None


@extension_model(HookModel)
class RPG_HookModel(BaseModel):
    """A hook's campaign. Hooks stay out of world_entities: plot hooks are often GM secrets (W9)."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")
    setting_id: Optional[str] = Field(None, description="FK → settings.id; with no campaign, the setting\'s canon (S6)")
    canon_level: Optional[str] = Field(None, description="contract/wiki.json canon_levels; unset until decided")
    is_template: Optional[bool] = Field(None, description="A template (W7): copied into campaigns, never a world fact")
    aliases: Optional[str] = Field(None, description="Other names it goes by, as JSON text (S4c)")
    keywords: Optional[str] = Field(None, description="What else wakes it in the AI's lorebook, as JSON text (S4c)")
    lore: Optional[str] = Field(None, description="Its lorebook activation (SillyTavern World Info's fields), as JSON text (S4d)")
    provenance: Optional[str] = Field(None, description="contract/wiki.json provenances: homebrew, official or adapted")
    source: Optional[str] = Field(None, description="The official title, publisher and product or page; none for homebrew")
    picture_url: Optional[str] = Field(None, description="Its picture by https link (fandom, wikis…), shown before an uploaded one")

    class Create(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        _source = field_validator("source")(checked_source)
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(checked_picture_url)

    class Update(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None
        is_template: Optional[bool] = None
        aliases: Optional[Any] = None
        keywords: Optional[Any] = None

        _aliases = field_validator("aliases")(names_text)
        _keywords = field_validator("keywords")(names_text)
        lore: Optional[Any] = None
        _lore = field_validator("lore")(lore_text)
        provenance: Optional[str] = None
        source: Optional[str] = None
        _provenance = field_validator("provenance")(lambda value: None if value is None else checked_provenance(value))
        # "" clears it (none leaves it as it is).
        picture_url: Optional[str] = None
        _picture_url = field_validator("picture_url")(lambda value: value if value is None else (checked_picture_url(value) or ""))

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None
        setting_id: Optional[StringSearchModel] = None
        canon_level: Optional[StringSearchModel] = None
        is_template: Optional[BooleanSearchModel] = None


class _Campaign(BaseModel):
    """A taxonomy record's campaign: none = shared across campaigns (a tag set reused everywhere)."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")
    setting_id: Optional[str] = Field(None, description="FK → settings.id; with no campaign, the setting\'s canon (S6)")
    canon_level: Optional[str] = Field(None, description="contract/wiki.json canon_levels; unset until decided")

    class Create(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        canon_level: Optional[str] = None

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None
        setting_id: Optional[StringSearchModel] = None
        canon_level: Optional[StringSearchModel] = None


@extension_model(TaxonModel)
class RPG_TaxonModel(_Campaign):
    """A taxon's campaign."""


@extension_model(StatusModel)
class RPG_StatusModel(_Campaign):
    """A status's campaign."""


@extension_model(PropertyKitModel)
class RPG_PropertyKitModel(BaseModel):
    """A property kit's campaign or setting (S4b): none = the owner's kit for any record."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = for any campaign")
    setting_id: Optional[str] = Field(None, description="FK → settings.id; a kit for that setting's records")

    class Create(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None
        setting_id: Optional[StringSearchModel] = None


# ---------------------------------------------------------------------------
# Session reports (rpg-ai A24): a journal of kind session_report in a campaign
# ---------------------------------------------------------------------------

MANAGER_OF_TYPE: dict[str, Any] = {
    "person": PersonManager,
    "location": LocationManager,
    "faction": FactionManager,
    "item": ItemManager,
    "journal": JournalManager,
    "hook": HookManager,
}
MAX_MENTIONS: int = LIMITS["report_mentions"]


class Mention(PlainModel):
    target_entity_type: str
    target_entity_id: str

    @field_validator("target_entity_type")
    @classmethod
    def _type(cls, value: str) -> str:
        if value not in ENTITY_TYPES:
            raise ValueError(f"An entity type is one of: {', '.join(ENTITY_TYPES)}")
        return value


class SessionReportIn(PlainModel):
    campaign_id: str
    title: str
    body: str | list[Any]
    occurred_at: Optional[datetime] = None
    session_number: Optional[int] = None
    mentions: list[Mention] = []

    _title = field_validator("title")(checked_name)

    @field_validator("mentions")
    @classmethod
    def _few(cls, value: list[Mention]) -> list[Mention]:
        if len(value) > MAX_MENTIONS:
            raise ValueError(f"At most {MAX_MENTIONS} mentions")
        return value


class SessionReportEnvelope(PlainModel):
    session_report: SessionReportIn


class SessionReportOut(PlainModel):
    id: str
    campaign_id: Optional[str]
    title: str
    body: str
    text: str
    occurred_at: Optional[datetime]
    session_number: Optional[int]
    mentions: list[Mention]
    updated_at: Optional[datetime]


class SessionReportOutEnvelope(PlainModel):
    session_report: SessionReportOut


# The framework's optional extensions rpg_core reads when they're there, each by a model of theirs:
# a composing app may name an extension whose models it never registered (VTT, 2026-11-21: every
# start failed "No matching type found in registry for MetadataModel!"), so a name alone isn't proof.
_EXTENSION_MODELS = {
    "metadata": ("zephyrex.extensions.metadata.BLL_Metadata", "MetadataModel"),
    "attachments": ("zephyrex.extensions.attachments.BLL_Attachments", "AttachmentModel"),
}


def _serves(model_registry: Any, extension: str) -> bool:
    """The app loads ``extension`` and its model is registered, so its managers will work."""
    import importlib

    if extension not in model_registry.loaded_extension_names():
        return False
    module, name = _EXTENSION_MODELS[extension]
    try:
        model_registry.apply(getattr(importlib.import_module(module), name))
    except (ImportError, AttributeError, TypeError):
        return False
    return True


def _manager(model_registry: Any, requester_id: str, manager: Any) -> Any:
    return manager(requester_id=requester_id, model_registry=model_registry)


def _mentions_in(entry: Any) -> list[Mention]:
    found: list[Mention] = []

    def walk(nodes: Any) -> None:
        for node in nodes or []:
            if isinstance(node, dict):
                if node.get("type") == "mention" and node.get("target_entity_type") and node.get("target_entity_id"):
                    found.append(Mention(target_entity_type=node["target_entity_type"], target_entity_id=node["target_entity_id"]))
                walk(node.get("children"))

    walk(entry)
    return found


def write_session_report(model_registry: Any, requester_id: str, report: SessionReportIn) -> str:
    """Write ``report`` into its campaign as a session-report journal; its id. The campaign must be
    the requester's (404 otherwise), and every mention one of its records (422 otherwise)."""
    _manager(model_registry, requester_id, CampaignManager).get(id=report.campaign_id)
    named: list[dict[str, str]] = []
    for mention in report.mentions:
        try:
            record = _manager(model_registry, requester_id, MANAGER_OF_TYPE[mention.target_entity_type]).get(id=mention.target_entity_id)
        except HTTPException as error:
            raise HTTPException(status_code=422, detail=f"No {mention.target_entity_type} {mention.target_entity_id} to mention") from error
        if getattr(record, "campaign_id", None) != report.campaign_id:
            raise HTTPException(status_code=422, detail=f"{record.name} is not in this campaign")
        named.append({**mention.model_dump(), "name": str(record.name)})
    journal = _manager(model_registry, requester_id, JournalManager).create(
        name=report.title,
        entry=report_entry(report.body, named),
        kind="session_report",
        campaign_id=report.campaign_id,
        occurred_at=report.occurred_at,
        session_number=report.session_number,
    )
    return str(journal.id)


def read_session_report(model_registry: Any, requester_id: str, report_id: str) -> SessionReportOut:
    """A session report as its review sheet reads it (404 when it isn't the requester's report)."""
    import json

    journal = _manager(model_registry, requester_id, JournalManager).get(id=report_id)
    if getattr(journal, "kind", None) != "session_report":
        raise HTTPException(status_code=404, detail="Not a session report")
    entry = json.loads(journal.entry) if journal.entry else []
    return SessionReportOut(
        id=str(journal.id),
        campaign_id=getattr(journal, "campaign_id", None),
        title=str(journal.name),
        body=journal.entry or "[]",
        text=journal.description or "",
        occurred_at=journal.occurred_at,
        session_number=journal.session_number,
        mentions=_mentions_in(entry),
        updated_at=journal.updated_at,
    )


class SessionReportManager(AbstractBLLManager[Any], RouterMixin):
    """REST for rpg-ai's session reports, for clients without abilities: POST /v1/session_report
    writes one, GET /v1/session_report/{report_id} reads it back."""

    prefix: ClassVar[str | None] = "/v1/session_report"
    tags: ClassVar[list[str] | None] = ["Session reports"]
    routes_to_register: ClassVar[list[RouteType] | None] = []

    @custom_route(
        method="POST",
        path="",
        input_model=SessionReportEnvelope,
        output_model=SessionReportOutEnvelope,
        status_code=201,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Session reports",),
        summary="Write a session report into a campaign (a journal of kind session_report)",
    )
    def write_route(self, body: SessionReportEnvelope) -> SessionReportOutEnvelope:
        report_id = write_session_report(self.model_registry, str(self.requester.id), body.session_report)
        return SessionReportOutEnvelope(session_report=read_session_report(self.model_registry, str(self.requester.id), report_id))

    @custom_route(
        method="GET",
        path="/{report_id}",
        output_model=SessionReportOutEnvelope,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Session reports",),
        summary="A session report, for its review sheet",
    )
    def read_route(self, report_id: str) -> SessionReportOutEnvelope:
        return SessionReportOutEnvelope(session_report=read_session_report(self.model_registry, str(self.requester.id), report_id))



# ---------------------------------------------------------------------------
# World entities (rpg-ai A15): a campaign's changes since a time, for a lorebook sync
# ---------------------------------------------------------------------------
#
# The same answer as the lite edition's (client/src/lib/worldEntities.ts): each record as
# {id, kind, name, aliases, keywords, summary, picture, updated_at, deleted} (and a person's voice),
# paged by (changed_at, id).
# Built on the framework's changes() per manager, which keeps list's VIEW rule and includes the
# caller's own tombstones.

WORLD_ENTITY_MANAGERS: dict[str, Any] = {
    "location": LocationManager,
    "person": PersonManager,
    "faction": FactionManager,
    "item": ItemManager,
    "journal": JournalManager,
}
DEFAULT_LIMIT = 100
# The role a record's own picture takes (contract/wiki.json attachment_roles).
PRIMARY_IMAGE = ATTACHMENT_ROLES[0]
MAX_LIMIT = 500


class WorldEntity(PlainModel):
    id: str
    kind: str
    name: str
    aliases: list[str]
    summary: str
    picture: Optional[str]
    updated_at: datetime
    deleted: bool
    setting_id: Optional[str] = None
    # Canon (S6): a setting's record with no campaign, which anyone in the setting would know.
    canon: bool = False
    canon_level: Optional[str] = None
    # S4c: what else wakes it in the AI's lorebook (beyond name and aliases), and a person's voice.
    keywords: list[str] = []
    voice: Optional[dict[str, Any]] = None
    # A person's TTS voice id (operator, 2026-11-23: "A voice per character"); none is the default.
    tts_voice: Optional[str] = None
    # A person's schedule and motivations (the GM side's world tick; gm_only as the record is).
    routine: Optional[list[dict[str, Any]]] = None
    motivations: Optional[list[str]] = None
    # S4d: its lorebook activation (SillyTavern World Info's fields), or none.
    lore: Optional[dict[str, Any]] = None
    # Where it came from: homebrew, official or adapted, and its source.
    provenance: str = HOMEBREW
    source: Optional[str] = None
    # For the GM and narrator only (its private "GM only" property is true): never a player's prompt.
    gm_only: bool = False
    # Its tag names (rpg-ai finds the party by "PC"), and a person's ties to other people.
    tags: list[str] = []
    relationships: Optional[list[dict[str, Any]]] = None
    # Where a person is (a scenario's starting position, then play's), and a place's (or an
    # organisation's) parent in its tree: who's present in a scene is who's at its place or inside it.
    location_id: Optional[str] = None
    parent_id: Optional[str] = None


class WorldEntitiesPage(PlainModel):
    world_entities: list[WorldEntity]
    next: Optional[str]


def _cursor_of(entity: WorldEntity) -> str:
    import base64

    return base64.urlsafe_b64encode(f"{entity.updated_at.isoformat()}|{entity.id}".encode()).decode().rstrip("=")


def _read_cursor(cursor: str) -> tuple[datetime, str]:
    import base64

    try:
        text = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        stamp, _, entity_id = text.partition("|")
        if not entity_id:
            raise ValueError(cursor)
        return datetime.fromisoformat(stamp), entity_id
    except (ValueError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=422, detail="after is not a cursor") from error


def _naive(moment: datetime) -> datetime:
    """Stamps compared as UTC without a zone (the database's own stamps are naive UTC)."""
    from datetime import timezone

    return moment.astimezone(timezone.utc).replace(tzinfo=None) if moment.tzinfo else moment


def _checked_page(kinds: Optional[list[str]], limit: int) -> list[str]:
    if not 1 <= limit <= MAX_LIMIT:
        raise HTTPException(status_code=422, detail=f"limit is 1 to {MAX_LIMIT}")
    wanted = kinds or list(WORLD_ENTITY_MANAGERS)
    unknown = [kind for kind in wanted if kind not in WORLD_ENTITY_MANAGERS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown kinds: {', '.join(unknown)}")
    return wanted


def _entity(kind: str, record: Any, changed_at: datetime, deleted: bool) -> WorldEntity:
    """A record as rpg-ai's lorebook reads it (the sync's and the by-id read's one shaping)."""
    campaign = getattr(record, "campaign_id", None)
    return WorldEntity(
        id=str(record.id),
        kind=kind,
        name=str(record.name or ""),
        aliases=stored_names(getattr(record, "aliases", None)),
        keywords=stored_names(getattr(record, "keywords", None)),
        voice=stored_voice(getattr(record, "voice", None)) if kind == "person" else None,
        tts_voice=(getattr(record, "tts_voice", None) or None) if kind == "person" else None,
        routine=stored_routine(getattr(record, "routine", None)) if kind == "person" else None,
        motivations=stored_motivations(getattr(record, "motivations", None)) if kind == "person" else None,
        lore=stored_lore(getattr(record, "lore", None)),
        summary=summary(getattr(record, "description", None)),
        # Its picture by link, as it is; else _with_pictures fills its newest upload.
        picture=None if deleted else getattr(record, "picture_url", None) or None,
        updated_at=_naive(changed_at),
        deleted=deleted,
        setting_id=getattr(record, "setting_id", None),
        canon=campaign is None and getattr(record, "setting_id", None) is not None,
        canon_level=getattr(record, "canon_level", None),
        location_id=getattr(record, "location_id", None) if kind == "person" else None,
        parent_id=getattr(record, "parent_id", None) if kind in ("location", "faction") else None,
        provenance=getattr(record, "provenance", None) or HOMEBREW,
        source=getattr(record, "source", None),
    )


def _gather(
    model_registry: Any,
    requester_id: str,
    wanted: list[str],
    filters: dict[str, Any],
    canon_only: bool,
    start: Optional[datetime],
    floor: Optional[tuple[datetime, str]],
    limit: int,
    excluded: frozenset[str] = frozenset(),
) -> list[WorldEntity]:
    """The changes matching ``filters`` for each kind, past the cursor; with ``canon_only``, only
    records with no campaign (a setting's canon); never the ``excluded`` (another era's canon)."""
    found: list[WorldEntity] = []
    for kind in wanted:
        manager = _manager(model_registry, requester_id, WORLD_ENTITY_MANAGERS[kind])
        taken, page_after = 0, None
        while taken <= limit:
            page = manager.changes(since=start, after=page_after, limit=limit + 1, **filters)
            for change in page.changes:
                record = change.record
                campaign = getattr(record, "campaign_id", None)
                if canon_only and campaign is not None:
                    continue
                if str(getattr(record, "id", "")) in excluded:
                    continue
                # A template (S4b, W7) is copied into campaigns, never a world fact: rpg-ai never sees it.
                if getattr(record, "is_template", None):
                    continue
                entity = _entity(kind, record, change.changed_at, change.deleted_at is not None)
                if floor and (entity.updated_at, entity.id) <= floor:
                    continue
                found.append(entity)
                taken += 1
            if not page.next:
                break
            page_after = page.next
    return found


def _with_pictures(model_registry: Any, shown: list[WorldEntity]) -> list[WorldEntity]:
    """S2c (rpg-ai A31): each record's picture, its newest primary_image attachment's content path,
    in one query for the page (as SYSTEM: the caller already sees each record, and so its picture).
    None for a record without one, for a deleted asset, and where the attachments extension isn't
    loaded."""
    if not _serves(model_registry, "attachments") or not shown:
        return shown
    from zephyrex.extensions.attachments.BLL_Attachments import (  # type: ignore[import-not-found]
        AssetManager,
        AssetModel,
        AttachmentManager,
        AttachmentModel,
    )
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    system = env("SYSTEM_ID")
    links = AttachmentManager(requester_id=system, model_registry=model_registry).list(
        role=PRIMARY_IMAGE,
        filters=[FieldComparison(AttachmentModel, "target_entity_id", "in", sorted({entity.id for entity in shown}))],
    )
    present = {
        str(asset.id)
        for asset in AssetManager(requester_id=system, model_registry=model_registry).list(
            filters=[FieldComparison(AssetModel, "id", "in", sorted({str(link.asset_id) for link in links}))]
        )
    } if links else set()
    newest: dict[tuple[str, str], str] = {}
    for link in sorted(links, key=lambda link: str(link.created_at)):
        if str(link.asset_id) in present:
            newest[(link.target_entity_type, link.target_entity_id)] = str(link.asset_id)
    for entity in shown:
        if entity.picture is not None:
            # A picture by link is the record's choice, before any upload.
            continue
        asset_id = newest.get((entity.kind, entity.id))
        entity.picture = None if asset_id is None or entity.deleted else f"/v1/asset/{asset_id}/content"
    return shown


def _gm_only(model_registry: Any, ids: list[str]) -> set[tuple[str, str]]:
    """Which of the records are kept to the GM: their private "GM only" property (contract
    gm_only_property) is "true", in one query (as SYSTEM: the caller already sees each record).
    Where the metadata extension isn't loaded, none are."""
    if not _serves(model_registry, "metadata") or not ids:
        return set()
    # The metadata extension's own row manager (its record_metadata routes have no model of their own).
    from zephyrex.extensions.metadata.BLL_Metadata import MetadataManager  # type: ignore[import-not-found]
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    rows = MetadataManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)
    return {
        (row.target_entity_type, row.target_entity_id)
        for row in rows.list(key=GM_ONLY_PROPERTY, filters=[FieldComparison(rows.Model, "target_entity_id", "in", sorted(set(ids)))]) or []
        if str(row.value).strip().lower() == "true"
    }


def _with_secrecy(model_registry: Any, shown: list[WorldEntity]) -> list[WorldEntity]:
    """Each record kept to the GM, marked gm_only."""
    secret = _gm_only(model_registry, [entity.id for entity in shown])
    for entity in shown:
        entity.gm_only = (entity.kind, entity.id) in secret
    return shown


def _with_tags_and_ties(model_registry: Any, requester_id: str, shown: list[WorldEntity]) -> list[WorldEntity]:
    """Each record's tag names (rpg-ai finds the party by "PC"), and each person's ties to other
    people ({to_id, kind, note}), read under the requester's access, one query each for the page. A
    tie with a GM-only end is left out: it would tell a player what only the GM knows."""
    from zephyrex.extensions.genealogy.BLL_Genealogy import RelationshipManager
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    if not shown:
        return shown
    ids = sorted({entity.id for entity in shown})
    links = _manager(model_registry, requester_id, EntityTaxonManager)
    rows = links.list(filters=[FieldComparison(links.Model, "target_entity_id", "in", ids)]) or []
    taxa = _manager(model_registry, requester_id, TaxonManager)
    names = {str(one.id): str(one.name or "") for one in (taxa.list(filters=[FieldComparison(taxa.Model, "id", "in", sorted({str(row.taxon_id) for row in rows}))]) or [])} if rows else {}
    tagged: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        name = names.get(str(row.taxon_id))
        if name:
            tagged.setdefault((row.target_entity_type, row.target_entity_id), []).append(name)
    people = [entity.id for entity in shown if entity.kind == "person"]
    ties = _manager(model_registry, requester_id, RelationshipManager)
    held = (ties.list(filters=[FieldComparison(ties.Model, "person_id", "in", people)]) or []) if people else []
    others = sorted({str(row.target_person_id) for row in held if getattr(row, "target_person_id", None)})
    secret = _gm_only(model_registry, people + others)
    by_person: dict[str, list[dict[str, Any]]] = {}
    for row in held:
        to = getattr(row, "target_person_id", None)
        if not to or ("person", str(to)) in secret or ("person", str(row.person_id)) in secret:
            continue
        by_person.setdefault(str(row.person_id), []).append({"to_id": str(to), "kind": row.kind, "note": (row.notes or "").strip() or None})
    for entity in shown:
        entity.tags = sorted(set(tagged.get((entity.kind, entity.id), [])))
        if entity.kind == "person":
            entity.relationships = by_person.get(entity.id, [])
    return shown


def _shown(model_registry: Any, shown: list[WorldEntity], requester_id: Optional[str] = None) -> list[WorldEntity]:
    """The page as rpg-ai reads it: each record's picture, whether it's the GM's alone, its tags and a
    person's ties."""
    shown = _with_secrecy(model_registry, _with_pictures(model_registry, shown))
    return shown if requester_id is None else _with_tags_and_ties(model_registry, requester_id, shown)


def _paged(found: list[WorldEntity], limit: int, model_registry: Any, requester_id: Optional[str] = None) -> WorldEntitiesPage:
    found.sort(key=lambda entity: (entity.updated_at, entity.id))
    shown = _shown(model_registry, found[:limit], requester_id)
    return WorldEntitiesPage(world_entities=shown, next=_cursor_of(shown[-1]) if len(found) > limit else None)


def _window(since: Optional[datetime], after: Optional[str]) -> tuple[Optional[datetime], Optional[tuple[datetime, str]]]:
    floor = _read_cursor(after) if after else None
    start = _naive(since) if since else None
    if floor and (start is None or floor[0] > start):
        start = floor[0]
    return start, floor


def world_entities(
    model_registry: Any,
    requester_id: str,
    campaign_id: str,
    since: Optional[datetime] = None,
    kinds: Optional[list[str]] = None,
    after: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    include_setting: bool = False,
) -> WorldEntitiesPage:
    """One page of the campaign's changed entities, oldest first, and the cursor for the next. With
    ``include_setting``, its setting's canon comes in the same pages (S6)."""
    wanted = _checked_page(kinds, limit)
    campaign = _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    start, floor = _window(since, after)
    found = _gather(model_registry, requester_id, wanted, {"campaign_id": campaign_id}, False, start, floor, limit)
    setting_id = getattr(campaign, "setting_id", None)
    if include_setting and setting_id:
        excluded = era_excluded(model_registry, requester_id, str(campaign.id))
        found += _gather(model_registry, requester_id, wanted, {"setting_id": setting_id}, True, start, floor, limit, excluded)
    return _paged(found, limit, model_registry, requester_id)


def era_excluded(model_registry: Any, requester_id: str, campaign_id: str) -> frozenset[str]:
    """The records another era holds, kept from this campaign's view of its setting's canon (operator,
    2026-11-23: Reality's eras work like the 40k lines; wiki_shared/Eras.py): none when the campaign
    has no era; else every record whose eras (taxa of kind era) it shares none of. Era-less canon is
    never excluded."""
    from zephyrex.extensions.wiki_shared.Eras import ERA, era_visible  # type: ignore[import-not-found]
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    taxa = {str(row.id): str(row.name or "") for row in _every(_manager(model_registry, requester_id, TaxonManager), [FieldComparison(TaxonModel, "kind", "eq", ERA)])}
    if not taxa:
        return frozenset()
    links = _manager(model_registry, requester_id, EntityTaxonManager)
    eras_of: dict[str, set[str]] = {}
    ids = sorted(taxa)
    for start in range(0, len(ids), 500):
        for row in _every(links, [FieldComparison(links.Model, "taxon_id", "in", ids[start : start + 500])]):
            eras_of.setdefault(str(row.target_entity_id), set()).add(taxa[str(row.taxon_id)])
    own = eras_of.get(str(campaign_id), set())
    if not own:
        return frozenset()
    return frozenset(target for target, eras in eras_of.items() if target != str(campaign_id) and not era_visible(eras, own))


def setting_canon(
    model_registry: Any,
    requester_id: str,
    setting_id: str,
    since: Optional[datetime] = None,
    kinds: Optional[list[str]] = None,
    after: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> WorldEntitiesPage:
    """One page of a setting's canon (its records with no campaign) changed since a time, tombstones
    included, oldest first: what rpg-ai's canon notices check against (S6)."""
    wanted = _checked_page(kinds, limit)
    _manager(model_registry, requester_id, SettingManager).get(id=setting_id)
    start, floor = _window(since, after)
    return _paged(_gather(model_registry, requester_id, wanted, {"setting_id": setting_id}, True, start, floor, limit), limit, model_registry, requester_id)


def world_entities_by_id(model_registry: Any, requester_id: str, ids: list[str]) -> WorldEntitiesPage:
    """The named records (rpg-ai's sandbox cast: persons from several campaigns, or a setting's
    canon), shaped as the sync shapes them, under the requester's access. An id the requester can't
    see, a deleted record, a template or an unknown id is simply absent; ``next`` is always none."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    try:
        wanted = entity_ids(ids)
    except EntityIdsError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    found: list[WorldEntity] = []
    for kind, manager_class in WORLD_ENTITY_MANAGERS.items():
        manager = _manager(model_registry, requester_id, manager_class)
        for record in manager.list(filters=[FieldComparison(manager.Model, "id", "in", wanted)]) or []:
            if getattr(record, "is_template", None):
                continue
            found.append(_entity(kind, record, getattr(record, "updated_at", None) or record.created_at, False))
    order = {entity_id: index for index, entity_id in enumerate(wanted)}
    found.sort(key=lambda entity: order[entity.id])
    return WorldEntitiesPage(world_entities=_shown(model_registry, found, requester_id), next=None)


# ---------------------------------------------------------------------------
# The world's activation index (operator, 2026-11-22: "Why is it reading the whole world instead of
# tag/relevance based injection?"): each record's keys (wiki_shared/WorldKeys), kept current by
# hooks, so a narrator's turn reads only the records its text names, never a whole setting.
# ---------------------------------------------------------------------------


class WorldKeyModel(ApplicationModel.Optional, UpdateMixinModel.Optional, metaclass=ModelMeta):
    """One activation key of one record: its name, an alias, a keyword, or "*" when always active."""

    Manager: ClassVar[Type["WorldKeyManager"]] = None
    table_comment: ClassVar[str] = "A record's activation key, for the narrator's relevance read (world_entities_matching)."

    key: Optional[str] = Field(None, description="Normalised: accents dropped, case folded, words single-spaced")
    target_entity_type: Optional[str] = Field(None, description="The record's type: location, person, faction, item or journal")
    target_entity_id: Optional[str] = Field(None, description="The record")
    campaign_id: Optional[str] = Field(None, description="The record's campaign; none for a setting's canon")
    setting_id: Optional[str] = Field(None, description="The record's setting, for its canon")

    class Create(BaseModel):
        key: str = Field(...)
        target_entity_type: str = Field(...)
        target_entity_id: str = Field(...)
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None

    class Update(BaseModel):
        pass

    class Search(ApplicationModel.Search):
        pass


class WorldKeyManager(AbstractBLLManager, RouterMixin):
    """Internal: written by rpg_core's hooks as SYSTEM, read by world_entities_matching."""

    _model = WorldKeyModel
    routes_to_register: ClassVar[list[RouteType] | None] = []


WorldKeyModel.Manager = WorldKeyManager


class LoreChunkModel(ApplicationModel.Optional, UpdateMixinModel.Optional, metaclass=ModelMeta):
    """One passage of one record, for the narrator's hybrid lore search (rpg_core 017). On Postgres
    the table also has tsv and embedding columns, written and read by SQL only (LoreSearch.py)."""

    Manager: ClassVar[Type["LoreChunkManager"]] = None
    table_comment: ClassVar[str] = "A passage of a record, for the narrator's hybrid lore search (lore_search)."

    target_entity_type: Optional[str] = Field(None, description="The record's type")
    target_entity_id: Optional[str] = Field(None, description="The record")
    name: Optional[str] = Field(None, description="The record's name (trigram-matched)")
    campaign_id: Optional[str] = Field(None, description="The record's campaign; none for a setting's canon")
    setting_id: Optional[str] = Field(None, description="The record's setting")
    game_system_id: Optional[str] = Field(None, description="The record's game system, when it has one")
    kind: Optional[str] = Field(None, description="The record's kind")
    source: Optional[str] = Field(None, description="Its source (a book), when it has one")
    page: Optional[int] = Field(None, description="The source's page, when known")
    position: Optional[int] = Field(None, description="The passage's place in the record, from 0")
    path: Optional[str] = Field(None, description="JSON: the record's name, then its headings")
    text: Optional[str] = Field(None, description="The passage")
    tokens: Optional[int] = Field(None, description="Its length in tokens (characters / 4)")
    embedded_model: Optional[str] = Field(None, description="The model that embedded it")
    embedded_at: Optional[datetime] = Field(None, description="When it was embedded; none until then")

    class Create(BaseModel):
        target_entity_type: str = Field(...)
        target_entity_id: str = Field(...)
        name: Optional[str] = None
        campaign_id: Optional[str] = None
        setting_id: Optional[str] = None
        game_system_id: Optional[str] = None
        kind: Optional[str] = None
        source: Optional[str] = None
        page: Optional[int] = None
        position: Optional[int] = None
        path: Optional[str] = None
        text: Optional[str] = None
        tokens: Optional[int] = None

    class Update(BaseModel):
        pass

    class Search(ApplicationModel.Search):
        pass


class LoreChunkManager(AbstractBLLManager, RouterMixin):
    """Internal: written by rpg_core's hooks as SYSTEM, read by lore_search."""

    _model = LoreChunkModel
    routes_to_register: ClassVar[list[RouteType] | None] = []


LoreChunkModel.Manager = LoreChunkManager

KEY_BATCH = 500


def _keys_of(record: Any) -> list[str]:
    from zephyrex.extensions.wiki_shared.WorldKeys import record_keys  # type: ignore[import-not-found]

    lore = stored_lore(getattr(record, "lore", None)) or {}
    return record_keys(str(getattr(record, "name", "") or ""), stored_names(getattr(record, "aliases", None)), stored_names(getattr(record, "keywords", None)), bool(lore.get("always_active")))


def _index_records(model_registry: Any, kind: str, records: list[Any], replace: bool = True) -> int:
    """These records' keys written (their old ones dropped first when ``replace``); templates and
    deleted records have none. Returns how many keys were written."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison
    from zephyrex.extensions.rpg_core.Scenarios import create_all  # type: ignore[import-not-found]

    keys = WorldKeyManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)
    ids = [str(record.id) for record in records]
    if replace and ids:
        for start in range(0, len(ids), KEY_BATCH):
            for row in keys.list(filters=[FieldComparison(keys.Model, "target_entity_id", "in", ids[start : start + KEY_BATCH])]) or []:
                keys.delete(id=str(row.id))
    rows = [
        {"key": key, "target_entity_type": kind, "target_entity_id": str(record.id), "campaign_id": getattr(record, "campaign_id", None), "setting_id": getattr(record, "setting_id", None)}
        for record in records
        if not getattr(record, "is_template", None) and not getattr(record, "deleted_at", None)
        for key in _keys_of(record)
    ]
    create_all(keys, rows)
    return len(rows)


def _keys_follow(kind: str) -> Any:
    """After a record of ``kind`` is made, changed or deleted, its keys and its lore passages follow."""

    def keys_follow(context: HookContext) -> None:
        from zephyrex.extensions.rpg_core.LoreSearch import index_lore  # type: ignore[import-not-found]

        registry = context.manager.model_registry

        def follow(registry: Any, kind: str, records: list[Any], replace: bool = True) -> None:
            # Its keys (world_entities_matching) and its passages (lore_search) together.
            _index_records(registry, kind, records, replace)
            index_lore(registry, kind, records, replace)

        if context.method_name == "delete":
            record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
            if record_id:
                follow(registry, kind, [type("Gone", (), {"id": str(record_id), "deleted_at": True})()])
            return
        if context.method_name == "update":
            # The record as it now stands (an update may answer without every field).
            record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
            if record_id:
                try:
                    follow(registry, kind, [context.manager.get(id=str(record_id))])
                except HTTPException:
                    pass
            return
        if context.method_name != "create":
            return
        result = context.result
        records = [one for one in (result if isinstance(result, list) else [result]) if one is not None and getattr(one, "id", None)]
        if records:
            follow(registry, kind, records, replace=False)

    keys_follow.__name__ = keys_follow.__qualname__ = f"world_keys_{kind}"
    return keys_follow




for _kind, _keyed in WORLD_ENTITY_MANAGERS.items():
    hook_bll(_keyed, timing=HookTiming.AFTER, priority=40)(_keys_follow(_kind))


class WorldEntitiesMatched(PlainModel):
    world_entities: list[WorldEntity]
    matched: dict[str, list[str]] = Field(..., description="Each record's keys the text named (\"*\" for always active)")


def world_entities_matching(
    model_registry: Any,
    requester_id: str,
    campaign_id: str,
    text: str,
    limit: int = 50,
    include_setting: bool = True,
    tags: Optional[list[str]] = None,
) -> WorldEntitiesMatched:
    """Only the campaign's records (and, with ``include_setting``, its setting's canon) whose name,
    alias or keyword the text names, plus the always-active ones: found through the key index (an
    indexed lookup of the text's word n-grams), never by reading the setting. ``tags`` keeps those
    tagged with any of the names. Most specific first (the longest key named), at most ``limit``
    (1 to 100); shaped and secret-kept as world_entities_by_id."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison
    from zephyrex.extensions.wiki_shared.WorldKeys import ALWAYS, text_grams  # type: ignore[import-not-found]

    limit = max(1, min(int(limit or 50), 100))
    campaign = _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    setting_id = str(getattr(campaign, "setting_id", "") or "")
    grams = sorted(text_grams(text) | {ALWAYS})
    keys = WorldKeyManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)
    excluded = era_excluded(model_registry, requester_id, str(campaign_id)) if include_setting else frozenset()
    matched: dict[str, list[str]] = {}
    kinds: dict[str, str] = {}
    for start in range(0, len(grams), KEY_BATCH):
        for row in keys.list(filters=[FieldComparison(keys.Model, "key", "in", grams[start : start + KEY_BATCH])]) or []:
            own = str(row.campaign_id or "") == str(campaign_id)
            canon = include_setting and not row.campaign_id and setting_id and str(row.setting_id or "") == setting_id and str(row.target_entity_id) not in excluded
            if own or canon:
                matched.setdefault(str(row.target_entity_id), []).append(str(row.key))
                kinds[str(row.target_entity_id)] = str(row.target_entity_type)
    ranked = sorted(matched, key=lambda one: (-max(len(key.split()) if key != ALWAYS else 0 for key in matched[one]), one))
    wanted = {name.strip().casefold() for name in tags or [] if name.strip()}
    found: list[WorldEntity] = []
    for start in range(0, len(ranked), 100):
        if len(found) >= limit:
            break
        page = world_entities_by_id(model_registry, requester_id, ranked[start : start + 100]).world_entities
        found.extend(entity for entity in page if not wanted or wanted & {tag.casefold() for tag in entity.tags})
    found = found[:limit]
    return WorldEntitiesMatched(world_entities=found, matched={entity.id: sorted(set(matched[entity.id])) for entity in found})


# POST /v1/campaign/{id}/matching, attached once its answer's model exists (WorldEntity is defined
# after CampaignManager); routes are collected when the app starts.
@custom_route(
    method="POST",
    path="/{id}/matching",
    input_model=MatchingEnvelope,
    output_model=WorldEntitiesMatched,
    authentication_type="jwt",
    expose_in=(ExposeIn.REST,),
    openapi_tags=("Campaigns",),
    summary="The campaign's records (and its setting's canon) whose names, aliases or keywords the text names, plus the always-active",
)
def matching_route(self, id: str, matching: MatchingAsk) -> Any:
    asked = MatchingAsk.model_validate(matching)
    return world_entities_matching(self.model_registry, str(self.requester.id), id, asked.text, asked.limit, asked.include_setting, asked.tags)


CampaignManager.matching_route = matching_route  # type: ignore[attr-defined]


def rebuild_world_keys(model_registry: Any, requester_id: str) -> dict[str, int]:
    """The requester's records with no keys yet indexed (records made before the index existed,
    rpg_core 016); those already indexed stay as their hooks keep them. {kind: records indexed}."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    keys = WorldKeyManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)
    indexed: dict[str, int] = {}
    for kind, manager_class in WORLD_ENTITY_MANAGERS.items():
        records = _every(_manager(model_registry, requester_id, manager_class))
        held: set[str] = set()
        ids = [str(record.id) for record in records]
        for start in range(0, len(ids), KEY_BATCH):
            held.update(str(row.target_entity_id) for row in keys.list(filters=[FieldComparison(keys.Model, "target_entity_id", "in", ids[start : start + KEY_BATCH])]) or [])
        missing = [record for record in records if str(record.id) not in held and not getattr(record, "is_template", None) and not getattr(record, "deleted_at", None)]
        _index_records(model_registry, kind, missing, replace=False)
        indexed[kind] = len(missing)
    return indexed


# ---------------------------------------------------------------------------
# The world tick (operator, 2026-11-21): a campaign's clock, and people moved by its GM
# ---------------------------------------------------------------------------

MAX_CLOCK_ADVANCE: int = LIMITS["clock_advance_minutes"]
MAX_MOVE_REASON: int = LIMITS["move_reason_characters"]


def campaign_clock(model_registry: Any, requester_id: str, campaign_id: str) -> CampaignClock:
    """The campaign's in-world clock, under the requester's access (a new one is day 1, 08:00)."""
    campaign = _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    return CampaignClock(**clock(getattr(campaign, "clock_minutes", None)))


def advance_clock(model_registry: Any, requester_id: str, campaign_id: str, minutes: int, reason: Optional[str] = None) -> CampaignClock:
    """Its clock moved on by ``minutes``: the campaign's GM's to do (EDIT on the campaign)."""
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= MAX_CLOCK_ADVANCE:
        raise HTTPException(status_code=422, detail=f"The clock advances 1 to {MAX_CLOCK_ADVANCE} minutes at a time")
    campaigns = _manager(model_registry, requester_id, CampaignManager)
    held = clock(getattr(campaigns.get(id=campaign_id), "clock_minutes", None))["minutes"]
    # clock_minutes isn't a client's to set: a trusted update, under the same EDIT check and hooks.
    campaigns.update_trusted(campaign_id, clock_minutes=held + minutes)
    return CampaignClock(**clock(held + minutes), reason=(reason or "").strip() or None)


class PersonMoveModel(ApplicationModel.Optional, UpdateMixinModel.Optional, PersonModel.Reference.Optional, metaclass=ModelMeta):
    """A person moved by the GM side's world tick: from where, to where, when in-world, why, and by
    whom (its creator). The person's history of where they've been."""

    Manager: ClassVar[Type["PersonMoveManager"]] = None
    table_comment: ClassVar[str] = "A person moved by the GM: from where, to where, when in-world and why."

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; the campaign whose clock dated it")
    from_location_id: Optional[str] = Field(None, description="FK → locations.id; where they were (none: nowhere yet)")
    to_location_id: Optional[str] = Field(None, description="FK → locations.id; where they went")
    at_minutes: Optional[int] = Field(None, description="The campaign's clock when they moved")
    reason: Optional[str] = Field(None, description="Why they moved")

    class Create(BaseModel, PersonModel.Reference.ID.Optional):
        to_location_id: str = Field(...)
        reason: Optional[str] = None
        # Filled by _move_holds from the person and the campaign's clock, whatever a caller sends.
        from_location_id: Optional[str] = None
        campaign_id: Optional[str] = None
        at_minutes: Optional[int] = None

    class Update(BaseModel):
        reason: Optional[str] = None

    class Search(ApplicationModel.Search, PersonModel.Reference.ID.Search):
        pass


class PersonMoveManager(AbstractBLLManager, RouterMixin):
    _model = PersonMoveModel


PersonMoveModel.Manager = PersonMoveManager


def _move_holds(context: HookContext) -> None:
    """A move: to a place in the person's campaign or its setting's canon, by someone who may edit
    the person (the GM); the person goes there, and the row keeps where from and when."""
    if context.method_name != "create":
        return
    registry, requester = context.manager.model_registry, str(context.manager.requester.id)
    person_id, to = context.kwarg("person_id", default=None), context.kwarg("to_location_id", default=None)
    if not person_id or not to:
        raise HTTPException(status_code=422, detail="Name the person and where they go")
    reason = (context.kwarg("reason", default=None) or "").strip()
    if len(reason) > MAX_MOVE_REASON:
        raise HTTPException(status_code=422, detail=f"A move's reason has at most {MAX_MOVE_REASON} characters")
    people = _manager(registry, requester, PersonManager)
    person = people.get(id=person_id)
    place = _manager(registry, requester, LocationManager).get(id=to)
    campaign_id = getattr(person, "campaign_id", None)
    setting_id = getattr(person, "setting_id", None)
    if campaign_id and not setting_id:
        setting_id = getattr(_manager(registry, requester, CampaignManager).get(id=campaign_id), "setting_id", None)
    in_campaign = campaign_id is not None and getattr(place, "campaign_id", None) == campaign_id
    in_canon = getattr(place, "campaign_id", None) is None and setting_id is not None and getattr(place, "setting_id", None) == setting_id
    if not (in_campaign or in_canon):
        raise HTTPException(status_code=422, detail="That place isn't in the person's campaign or its setting")
    held = getattr(person, "location_id", None)
    people.update(id=person_id, location_id=to)
    context.kwargs.update(
        from_location_id=held,
        campaign_id=campaign_id,
        at_minutes=campaign_clock(registry, requester, campaign_id).minutes if campaign_id else None,
        reason=reason or None,
    )


hook_bll(PersonMoveManager, timing=HookTiming.BEFORE, priority=20)(_move_holds)


# ---------------------------------------------------------------------------
# What a player's character has learned (operator, 2026-11-24: "only player visible information and
# learned facts should be present there"): a known fact is one person's knowledge of one record, as
# text, or with none, that they know of it (which opens a record kept to the GM to that character).
# The GM writes them, from the record's page or as the AI GM through learn_fact.
# ---------------------------------------------------------------------------

MAX_KNOWN_FACT = int(LIMITS["known_fact_characters"])


class KnownFactModel(ApplicationModel.Optional, UpdateMixinModel.Optional, PersonModel.Reference.Optional, metaclass=ModelMeta):
    """One person's knowledge of one record: what they learned (text), or with none, that they know
    of it; and the session report it was learned in, when there is one."""

    Manager: ClassVar[Type["KnownFactManager"]] = None
    table_comment: ClassVar[str] = "What a person has learned about a record, or that they know of it."

    target_entity_type: Optional[str] = Field(None, description="The record's type: contract/wiki.json entity_types")
    target_entity_id: Optional[str] = Field(None, description="The record learned about")
    text: Optional[str] = Field(None, description="What they learned; none: they know of it")
    learned_in_journal_id: Optional[str] = Field(None, description="FK → journals.id; the session it was learned in")
    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; the person's campaign (set from the person)")

    class Create(BaseModel, PersonModel.Reference.ID):
        target_entity_type: str = Field(...)
        target_entity_id: str = Field(...)
        text: Optional[str] = None
        learned_in_journal_id: Optional[str] = None
        # Filled from the person, whatever a caller sends.
        campaign_id: Optional[str] = None

    class Update(BaseModel):
        text: Optional[str] = None
        learned_in_journal_id: Optional[str] = None

    class Search(ApplicationModel.Search, PersonModel.Reference.ID.Search):
        target_entity_type: Optional[StringSearchModel] = None
        target_entity_id: Optional[StringSearchModel] = None
        campaign_id: Optional[StringSearchModel] = None


class KnownFactManager(AbstractBLLManager, RouterMixin):
    _model = KnownFactModel


KnownFactModel.Manager = KnownFactManager


def _known_text(value: Any) -> Optional[str]:
    text = str(value).strip() if value is not None else ""
    if len(text) > MAX_KNOWN_FACT:
        raise HTTPException(status_code=422, detail=f"A known fact has at most {MAX_KNOWN_FACT} characters")
    return text or None


def _fact_holds(context: HookContext) -> None:
    """A known fact: of a record of a known type, by someone who may edit the person (the GM), in
    the person's campaign; its text trimmed (none: they know of it)."""
    from zephyrex.lib.RecordTarget import can_edit

    if context.method_name not in ("create", "update"):
        return
    registry, requester = context.manager.model_registry, str(context.manager.requester.id)
    if context.method_name == "update":
        if "text" in context.kwargs:
            context.kwargs["text"] = _known_text(context.kwargs.get("text"))
        return
    person_id, kind = context.kwarg("person_id", default=None), context.kwarg("target_entity_type", default=None)
    if not person_id or not context.kwarg("target_entity_id", default=None):
        raise HTTPException(status_code=422, detail="Name the person and the record they learned about")
    if kind not in ENTITY_TYPES:
        raise HTTPException(status_code=422, detail=f"A record's type is one of: {', '.join(ENTITY_TYPES)}")
    person = _manager(registry, requester, PersonManager).get(id=person_id)
    campaign_id = getattr(person, "campaign_id", None)
    if not campaign_id or not can_edit(registry, requester, "campaign", str(campaign_id)):
        raise HTTPException(status_code=403, detail="Only the campaign's GM says what its people know")
    context.kwargs.update(campaign_id=str(campaign_id), text=_known_text(context.kwarg("text", default=None)))


hook_bll(KnownFactManager, timing=HookTiming.BEFORE, priority=20)(_fact_holds)


class KnownFactLearned(PlainModel):
    known_fact: dict[str, Any]
    created: bool


def learn_fact(
    model_registry: Any,
    requester_id: str,
    person_id: str,
    target_entity_type: str,
    target_entity_id: str,
    text: Optional[str] = None,
    learned_in: Optional[str] = None,
) -> KnownFactLearned:
    """``person_id`` learns ``text`` about the record (or, with none, knows of it), learned in the
    session report ``learned_in``: the same fact twice is one row (created false). The person's
    campaign's GM's to do (the AI GM, when a scene reveals something)."""
    facts = _manager(model_registry, requester_id, KnownFactManager)
    wanted = _known_text(text)
    for row in facts.list(person_id=person_id, target_entity_id=target_entity_id) or []:
        if (row.text or None) == wanted:
            return KnownFactLearned(known_fact=row.model_dump(mode="json"), created=False)
    made = facts.create(person_id=person_id, target_entity_type=target_entity_type, target_entity_id=target_entity_id, text=wanted, learned_in_journal_id=learned_in)
    return KnownFactLearned(known_fact=made.model_dump(mode="json"), created=True)


# The most people current_attitudes reads among (the framework's MAX_BATCH_SIZE, as an __in list).
MAX_ATTITUDE_PEOPLE = 100


# current_attitudes' reserved key for an attitude toward the party (target_kind "party").
PARTY = "party"


def current_attitudes(model_registry: Any, requester_id: str, campaign_id: str, person_ids: list[str]) -> dict[str, dict[str, str]]:
    """How each of the campaign's ``person_ids`` regards each other one now, and the party
    (operator, 2026-11-24: "Combat sides should be based on character disposition"):
    {who_id: {"party": attitude, toward_id: attitude}}, the current disposition by resolved
    triggers else the default (wiki_shared/Dispositions.current), read as the scale's band. A pair
    with none, or "missing", is absent. Read only, and only what the requester may see; a person
    not in the campaign is left out."""
    from zephyrex.extensions.wiki_shared.Dispositions import band, current  # type: ignore[import-not-found]
    from zephyrex.extensions.world_narrative.BLL_WorldNarrative import DispositionManager  # type: ignore[import-not-found]
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    wanted = sorted({str(one).strip() for one in person_ids if str(one).strip()})
    if len(wanted) > MAX_ATTITUDE_PEOPLE:
        raise HTTPException(status_code=422, detail=f"At most {MAX_ATTITUDE_PEOPLE} people")
    if not wanted:
        return {}
    people = _manager(model_registry, requester_id, PersonManager)
    present = {str(row.id) for row in people.list(filters=[FieldComparison(people.Model, "id", "in", wanted)]) or [] if str(getattr(row, "campaign_id", "") or "") == campaign_id}
    if not present:
        return {}
    ids = sorted(present)
    held = _manager(model_registry, requester_id, DispositionManager)
    # Toward one another, and toward the party (VTT's stances fall back to it), in one read.
    rows = [
        row
        for row in held.list(filters=[FieldComparison(held.Model, "person_id", "in", ids)]) or []
        if (row.target_kind == "person" and str(row.target_person_id) in present and str(row.person_id) != str(row.target_person_id))
        or row.target_kind == PARTY
    ]
    rows.sort(key=lambda row: (row.created_at, str(row.id)))
    triggers = sorted({str(row.trigger_hook_id) for row in rows if row.trigger_hook_id})
    hooks = _manager(model_registry, requester_id, HookManager)
    resolved = {str(row.id): row.resolved_at for row in (hooks.list(filters=[FieldComparison(hooks.Model, "id", "in", triggers)]) or []) if triggers and row.resolved_at} if triggers else {}
    pairs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        toward = PARTY if row.target_kind == PARTY else str(row.target_person_id)
        pairs.setdefault((str(row.person_id), toward), []).append(
            {"attitude": row.attitude, "default": bool(row.is_default), "trigger": str(row.trigger_hook_id) if row.trigger_hook_id else None}
        )
    found: dict[str, dict[str, str]] = {}
    for (who, toward), entries in pairs.items():
        attitude = current(entries, resolved)
        if attitude is None or band(attitude) == "missing":
            continue
        found.setdefault(who, {})[toward] = band(attitude)
    return found


class PersonMoved(PlainModel):
    person_id: str
    from_location_id: Optional[str] = Field(None, alias="from")
    to_location_id: str = Field(..., alias="to")
    at: Optional[CampaignClock] = Field(None, description="The campaign's clock when they moved")
    reason: Optional[str] = None

    model_config = {"populate_by_name": True}


# A person the narrator brought in: kept GM only (players' prompts see the name alone) and marked as
# made in play, so the GM can flesh them out or fold them into someone they already had.
MADE_IN_PLAY_PROPERTY = "Made in play"


def ensure_person(model_registry: Any, requester_id: str, campaign_id: str, name: str, summary: Optional[str] = None) -> PersonEnsured:
    """The campaign's person called ``name`` (case aside), or a new one: an NPC with ``summary`` as
    its entry, GM only, made in play. The campaign's GM's to do (EDIT on the campaign), as the
    narrator's speakers are saved (Parity, 2026-11-21: unnamed NPCs who speak join the cast)."""
    from zephyrex.lib.RecordTarget import can_edit

    wanted = checked_name(name)
    # The campaign must be the requester's to read (404 otherwise) and to change (the GM's).
    _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    if not can_edit(model_registry, requester_id, "campaign", campaign_id):
        raise HTTPException(status_code=403, detail="Only the campaign's GM adds its people")
    people = _manager(model_registry, requester_id, PersonManager)
    folded = wanted.casefold()
    for row in people.list(campaign_id=campaign_id) or []:
        if str(row.name or "").strip().casefold() == folded:
            return PersonEnsured(id=str(row.id), name=str(row.name), created=False)
    line = (summary or "").strip()
    entry = json.dumps([{"type": "p", "children": [{"text": line}]}]) if line else None
    made = people.create(name=wanted, kind="npc", campaign_id=campaign_id, provenance=HOMEBREW, entry=entry)
    if _serves(model_registry, "metadata"):
        from zephyrex.extensions.metadata.BLL_Metadata import MetadataManager  # type: ignore[import-not-found]

        rows = MetadataManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)
        rows.create(
            entities=[
                {"target_entity_type": "person", "target_entity_id": str(made.id), "key": GM_ONLY_PROPERTY, "value": "true", "value_type": "boolean", "is_private": True},
                {"target_entity_type": "person", "target_entity_id": str(made.id), "key": MADE_IN_PLAY_PROPERTY, "value": "By the narrator", "value_type": "text", "is_private": True},
            ]
        )
    return PersonEnsured(id=str(made.id), name=str(made.name), created=True)


def _framing_of(model_registry: Any, requester_id: str, campaign: Any) -> tuple[str, str, str, list[str]]:
    """A campaign's own (description, public framing, GM framing, play styles)."""
    from zephyrex.extensions.wiki_shared.Framing import framing_parts  # type: ignore[import-not-found]
    from zephyrex.extensions.wiki_shared.Contract import PLAY_STYLE  # type: ignore[import-not-found]
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    campaign_id = str(campaign.id)
    framings = sorted(
        (row for row in _manager(model_registry, requester_id, JournalManager).list(campaign_id=campaign_id) or [] if row.kind == "campaign_framing" and not getattr(row, "is_template", None)),
        key=lambda row: str(row.name),
    )
    public, gm = "", ""
    if framings:
        public, gm = framing_parts(getattr(framings[0], "entry", None))
        if ("journal", str(framings[0].id)) in _gm_only(model_registry, [str(framings[0].id)]):
            public, gm = "", "\n\n".join(part for part in (public, gm) if part)
    links = _manager(model_registry, requester_id, EntityTaxonManager)
    taxon_ids = [str(row.taxon_id) for row in links.list(target_entity_type="campaign", target_entity_id=campaign_id) or []]
    styles: list[str] = []
    if taxon_ids:
        taxa = _manager(model_registry, requester_id, TaxonManager)
        styles = sorted(str(row.name) for row in taxa.list(filters=[FieldComparison(taxa.Model, "id", "in", taxon_ids)]) or [] if row.kind == PLAY_STYLE)
    return str(getattr(campaign, "description", "") or ""), public, gm, styles


def campaign_framing(model_registry: Any, requester_id: str, campaign_id: str) -> CampaignFraming:
    """A campaign's framing for the narrator (Parity, 2026-11-22: scenarios' framing went into the
    wiki campaign itself): its description, its framing journal's public text and GM part, its
    setting's tone, its play styles. A playthrough with none of its own takes its scenario's
    (from_scenario). The GM notes reach only its GM (EDIT on the campaign)."""
    from zephyrex.lib.RecordTarget import can_edit

    campaigns = _manager(model_registry, requester_id, CampaignManager)
    campaign = campaigns.get(id=campaign_id)
    description, framing, gm, styles = _framing_of(model_registry, requester_id, campaign)
    from_scenario = False
    scenario_id = getattr(campaign, "scenario_id", None)
    if not (description or framing or gm) and scenario_id:
        try:
            scenario = campaigns.get(id=str(scenario_id))
        except HTTPException:
            scenario = None
        if scenario is not None:
            held = _framing_of(model_registry, requester_id, scenario)
            if any(held[:3]):
                description, framing, gm = held[:3]
                styles = styles or held[3]
                from_scenario = True
    if not can_edit(model_registry, requester_id, "campaign", campaign_id):
        gm = ""
    setting = None
    if getattr(campaign, "setting_id", None):
        try:
            row = _manager(model_registry, requester_id, SettingManager).get(id=str(campaign.setting_id))
            setting = FramingSetting(id=str(row.id), name=str(row.name), tone=str(getattr(row, "description", "") or ""))
        except HTTPException:
            setting = None
    return CampaignFraming(
        campaign_id=str(campaign.id),
        name=str(campaign.name),
        description=description,
        framing=framing,
        gm_notes=gm,
        setting=setting,
        play_styles=styles,
        from_scenario=from_scenario,
    )


FILL_FIELDS = ("summary", "entry", "personality", "motive", "voice", "tts_voice", "picture")
ELEVATED_PROPERTY = "Elevated to"


def update_person(model_registry: Any, requester_id: str, person_id: str, fields: dict[str, Any], campaign_id: Optional[str] = None) -> PersonFilled:
    """A person filled in by an agent (Parity, 2026-11-22: the GM authors NPCs mid-play): summary
    and a Markdown entry become the entry (the summary its first paragraph); personality and voice
    their voice's personality and speech; motive one of their motivations; picture an https link
    (picture_url) or an uploaded asset's id (attached). Only what's given changes; it takes EDIT on
    the person, as any update."""
    from zephyrex.extensions.wiki_shared.Markdown import markdown_entry  # type: ignore[import-not-found]

    unknown = sorted(set(fields) - set(FILL_FIELDS))
    if unknown:
        raise HTTPException(status_code=422, detail=f"A person is filled with {', '.join(FILL_FIELDS)}; not {', '.join(unknown)}")
    people = _manager(model_registry, requester_id, PersonManager)
    person = people.get(id=person_id)
    if campaign_id is not None and str(getattr(person, "campaign_id", "") or "") != str(campaign_id):
        raise HTTPException(status_code=404, detail="PersonModel not found in this campaign")
    changes: dict[str, Any] = {}
    summary_line = str(fields.get("summary") or "").strip()
    if summary_line or fields.get("entry"):
        blocks = ([{"type": "p", "children": [{"text": summary_line}]}] if summary_line else []) + markdown_entry(str(fields.get("entry") or ""))
        changes["entry"] = blocks
    if fields.get("personality") or fields.get("voice"):
        held = stored_voice(getattr(person, "voice", None)) or {}
        if fields.get("personality"):
            held["personality"] = str(fields["personality"]).strip()
        if fields.get("voice"):
            held["speech"] = str(fields["voice"]).strip()
        changes["voice"] = held
    if fields.get("tts_voice") is not None:
        try:
            changes["tts_voice"] = tts_voice_text(fields["tts_voice"]) or ""
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
    if fields.get("motive"):
        motives = stored_motivations(getattr(person, "motivations", None))
        motive = str(fields["motive"]).strip()
        if motive not in motives:
            changes["motivations"] = [*motives, motive]
    picture = str(fields.get("picture") or "").strip()
    if picture.startswith("data:"):
        raise HTTPException(status_code=422, detail="Upload the picture first (POST /v1/asset/upload) and give its asset id")
    if picture.startswith("https://"):
        changes["picture_url"] = picture
    if changes:
        person = people.update(id=person_id, **changes)
    updated = sorted(key for key in fields if fields.get(key) or (key == "tts_voice" and fields.get(key) == ""))
    if picture and not picture.startswith("https://"):
        if not _serves(model_registry, "attachments"):
            raise HTTPException(status_code=422, detail="This back end keeps no uploaded pictures: give an https link")
        from zephyrex.extensions.attachments.BLL_Attachments import AttachmentManager  # type: ignore[import-not-found]

        _manager(model_registry, requester_id, AttachmentManager).create(asset_id=picture, target_entity_type="person", target_entity_id=person_id, role="primary_image")
    return PersonFilled(id=str(person.id), name=str(person.name), updated=updated)


def _by_name(rows: list[Any]) -> dict[str, Any]:
    return {str(row.name).strip().casefold(): row for row in rows}


def elevate_person(model_registry: Any, requester_id: str, person_id: str, campaign_id: Optional[str] = None) -> PersonElevated:
    """A playthrough's person copied into its scenario so later playthroughs have them (operator,
    2026-11-22: NPCs authored mid-play, "elevate to scenario" on their profile). Their fields,
    properties, tags and pictures come along; their place and their ties to organisations and people
    are turned to the scenario's own of the same name (left out where it has none). The campaign's
    person is marked "Elevated to" its counterpart; a second call, or one for a person the scenario
    already has by name, makes nothing and says which. The GM's of both (EDIT on each)."""
    from zephyrex.lib.RecordTarget import can_edit
    from zephyrex.extensions.genealogy.BLL_Genealogy import RelationshipManager

    people = _manager(model_registry, requester_id, PersonManager)
    person = people.get(id=person_id)
    own = str(getattr(person, "campaign_id", "") or "")
    if not own or (campaign_id is not None and own != str(campaign_id)):
        raise HTTPException(status_code=422, detail="Only a campaign's person is elevated to its scenario")
    campaigns = _manager(model_registry, requester_id, CampaignManager)
    campaign = campaigns.get(id=own)
    scenario_id = str(getattr(campaign, "scenario_id", "") or "")
    if not scenario_id:
        raise HTTPException(status_code=422, detail="This campaign isn't a playthrough of a scenario")
    if not (can_edit(model_registry, requester_id, "campaign", own) and can_edit(model_registry, requester_id, "campaign", scenario_id)):
        raise HTTPException(status_code=403, detail="Only the scenario's GM elevates its people")
    rows = MetadataManagerOf(model_registry)
    held = {str(row.key): row for row in (rows.list(target_entity_type="person", target_entity_id=person_id) or [])} if rows is not None else {}
    if ELEVATED_PROPERTY in held:
        try:
            twin = people.get(id=str(held[ELEVATED_PROPERTY].value))
            if str(twin.campaign_id) == scenario_id:
                return PersonElevated(person_id=person_id, scenario_person_id=str(twin.id), scenario_id=scenario_id, created=False)
        except HTTPException:
            pass
    theirs = _by_name(people.list(campaign_id=scenario_id) or [])
    existing = theirs.get(str(person.name).strip().casefold())
    if existing is not None:
        _mark_elevated(rows, person_id, str(existing.id))
        return PersonElevated(person_id=person_id, scenario_person_id=str(existing.id), scenario_id=scenario_id, created=False)

    writable = set(people._model.Create.model_fields)
    fields = {key: value for key, value in person.model_dump().items() if key in writable and value is not None and key not in ("id", "user_id", "campaign_id", "location_id", "is_template")}
    if getattr(person, "location_id", None):
        try:
            place = _manager(model_registry, requester_id, LocationManager).get(id=str(person.location_id))
            match = _by_name(_manager(model_registry, requester_id, LocationManager).list(campaign_id=scenario_id) or []).get(str(place.name).strip().casefold())
            if match is not None:
                fields["location_id"] = str(match.id)
            elif not getattr(place, "campaign_id", None):
                fields["location_id"] = str(place.id)  # the setting's canon: shared
        except HTTPException:
            pass
    made = people.create(**fields, campaign_id=scenario_id)
    new_id = str(made.id)
    # Tags: a campaign's own tag becomes the scenario's of the same name and kind (made if missing).
    taxa = _manager(model_registry, requester_id, TaxonManager)
    links = _manager(model_registry, requester_id, EntityTaxonManager)
    for link in links.list(target_entity_type="person", target_entity_id=person_id) or []:
        try:
            taxon = taxa.get(id=str(link.taxon_id))
        except HTTPException:
            continue
        target = str(taxon.id)
        if str(getattr(taxon, "campaign_id", "") or "") == own:
            same = [row for row in taxa.list(campaign_id=scenario_id) or [] if str(row.name) == str(taxon.name) and row.kind == taxon.kind]
            target = str(same[0].id) if same else str(taxa.create(name=taxon.name, kind=taxon.kind, campaign_id=scenario_id).id)
        links.create(taxon_id=target, target_entity_type="person", target_entity_id=new_id)
    # Ties to organisations and people: to the scenario's of the same name, or the setting's canon.
    ties = _manager(model_registry, requester_id, RelationshipManager)
    factions = _by_name(_manager(model_registry, requester_id, FactionManager).list(campaign_id=scenario_id) or [])
    for tie in ties.list(person_id=person_id) or []:
        tie_fields = {key: value for key, value in tie.model_dump().items() if key in set(ties._model.Create.model_fields) and value is not None and key not in ("id", "user_id", "person_id")}
        for key, manager_class, pool in (("target_faction_id", FactionManager, factions), ("target_person_id", PersonManager, theirs)):
            other = tie_fields.get(key)
            if not other:
                continue
            try:
                row = _manager(model_registry, requester_id, manager_class).get(id=str(other))
            except HTTPException:
                tie_fields.pop(key)
                continue
            if getattr(row, "campaign_id", None):
                match = pool.get(str(row.name).strip().casefold())
                if match is None:
                    tie_fields.pop(key)
                else:
                    tie_fields[key] = str(match.id)
        if tie_fields.get("target_faction_id") or tie_fields.get("target_person_id"):
            ties.create(person_id=new_id, **tie_fields)
    # Properties (not the marks of play) and pictures.
    if rows is not None:
        kept = [row for key, row in held.items() if key not in (ELEVATED_PROPERTY, MADE_IN_PLAY_PROPERTY)]
        if kept:
            from zephyrex.extensions.rpg_core.Scenarios import create_all  # type: ignore[import-not-found]

            create_all(rows, [{"target_entity_type": "person", "target_entity_id": new_id, "key": row.key, "value": row.value, "value_type": row.value_type, "ordinal": row.ordinal, "is_private": row.is_private} for row in kept])
    if _serves(model_registry, "attachments"):
        from zephyrex.extensions.attachments.BLL_Attachments import AttachmentManager  # type: ignore[import-not-found]
        from zephyrex.extensions.rpg_core.Scenarios import touching  # type: ignore[import-not-found]

        pictures = _manager(model_registry, requester_id, AttachmentManager)
        for row in touching(pictures, ("target_entity_id",), [person_id]):
            pictures.create(asset_id=str(row.asset_id), target_entity_type="person", target_entity_id=new_id, role=str(row.role))
    _mark_elevated(rows, person_id, new_id)
    return PersonElevated(person_id=person_id, scenario_person_id=new_id, scenario_id=scenario_id, created=True)


def MetadataManagerOf(model_registry: Any) -> Any:
    """The metadata extension's row manager as SYSTEM, or none where it isn't served."""
    if not _serves(model_registry, "metadata"):
        return None
    from zephyrex.extensions.metadata.BLL_Metadata import MetadataManager  # type: ignore[import-not-found]

    return MetadataManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)


def _mark_elevated(rows: Any, person_id: str, scenario_person_id: str) -> None:
    """The campaign's person marked with its scenario counterpart (private), replacing a stale mark."""
    if rows is None:
        return
    for row in rows.list(target_entity_type="person", target_entity_id=person_id, key=ELEVATED_PROPERTY) or []:
        rows.delete(id=str(row.id))
    rows.create(target_entity_type="person", target_entity_id=person_id, key=ELEVATED_PROPERTY, value=scenario_person_id, value_type="text", ordinal=0, is_private=True)


def move_person(model_registry: Any, requester_id: str, person_id: str, location_id: str, reason: Optional[str] = None) -> PersonMoved:
    """The person moved to ``location_id`` (the GM's to do), recorded in their history."""
    move = _manager(model_registry, requester_id, PersonMoveManager).create(person_id=person_id, to_location_id=location_id, reason=reason)
    return PersonMoved(
        person_id=person_id,
        from_location_id=move.from_location_id,
        to_location_id=str(move.to_location_id),
        at=CampaignClock(**clock(move.at_minutes)) if move.at_minutes is not None else None,
        reason=move.reason,
    )


# ---------------------------------------------------------------------------
# A campaign's documents (Parity's data bank): each record's full text, journals first
# ---------------------------------------------------------------------------

DOCUMENT_MANAGERS: dict[str, Any] = {
    "journal": JournalManager,
    "location": LocationManager,
    "person": PersonManager,
    "faction": FactionManager,
    "item": ItemManager,
    "hook": HookManager,
}


class CampaignDocument(PlainModel):
    id: str
    kind: str = Field(..., description="The record's type: journal, location, person, faction, item or hook")
    name: str
    text: str = Field(..., description="Its entry's full plain text")
    gm_only: bool = Field(False, description="Kept to the GM: never a player's prompt")


class CampaignDocuments(PlainModel):
    campaign_documents: list[CampaignDocument]


def campaign_documents(model_registry: Any, requester_id: str, campaign_id: str) -> CampaignDocuments:
    """The full plain text of each of the campaign's records under the requester's access, journals
    first (contract/document-cases.json); templates and records with no text left out. A campaign
    the requester can't see is a 404."""
    _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    records: list[dict[str, Any]] = []
    for kind in DOCUMENT_KINDS:
        manager = _manager(model_registry, requester_id, DOCUMENT_MANAGERS[kind])
        records.extend(
            {"id": str(row.id), "kind": kind, "name": str(row.name or ""), "text": getattr(row, "description", None)}
            for row in manager.list(campaign_id=campaign_id) or []
            if not getattr(row, "is_template", None)
        )
    documents = ordered_documents(records)
    secret = _gm_only(model_registry, [document["id"] for document in documents])
    return CampaignDocuments(
        campaign_documents=[CampaignDocument(**document, gm_only=(document["kind"], document["id"]) in secret) for document in documents]
    )


class CampaignDocumentManager(AbstractBLLManager[Any], RouterMixin):
    """REST for Parity's data bank: GET /v1/campaign_document?campaign_id=."""

    prefix: ClassVar[str | None] = "/v1/campaign_document"
    tags: ClassVar[list[str] | None] = ["Campaign documents"]
    routes_to_register: ClassVar[list[RouteType] | None] = []

    @custom_route(
        method="GET",
        path="",
        output_model=CampaignDocuments,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaign documents",),
        summary="The full text of each of a campaign's records, journals first",
    )
    def list_route(self, campaign_id: str) -> CampaignDocuments:
        return campaign_documents(self.model_registry, str(self.requester.id), campaign_id)


class WorldEntityManager(AbstractBLLManager[Any], RouterMixin):
    """REST for rpg-ai's lorebook sync: GET /v1/world_entity."""

    prefix: ClassVar[str | None] = "/v1/world_entity"
    tags: ClassVar[list[str] | None] = ["World entities"]
    routes_to_register: ClassVar[list[RouteType] | None] = []

    @custom_route(
        method="GET",
        path="",
        output_model=WorldEntitiesPage,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("World entities",),
        summary="A campaign's (or a setting's canon) places, people, factions, items and journals changed since a time, tombstones included",
    )
    def list_route(
        self,
        campaign_id: Optional[str] = None,
        setting_id: Optional[str] = None,
        ids: Optional[str] = None,
        include_setting: bool = False,
        since: Optional[datetime] = None,
        kinds: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> WorldEntitiesPage:
        """?campaign_id= (with &include_setting=true for its setting's canon too), ?setting_id= for
        a setting's canon alone, or ?ids=a,b for the named records wherever they are."""
        wanted = [kind for kind in kinds.split(",") if kind] if kinds else None
        requester = str(self.requester.id)
        if [campaign_id, setting_id, ids].count(None) != 2:
            raise HTTPException(status_code=422, detail="Name a campaign_id, a setting_id or ids")
        if ids is not None:
            return world_entities_by_id(self.model_registry, requester, ids.split(","))
        if setting_id is not None:
            return setting_canon(self.model_registry, requester, setting_id, since=since, kinds=wanted, after=after, limit=limit)
        return world_entities(
            self.model_registry, requester, campaign_id or "", since=since, kinds=wanted, after=after, limit=limit, include_setting=include_setting
        )



# ---------------------------------------------------------------------------
# Plot state (W57): every hook in a campaign with its state, for a GM's board, VTT and rpg-ai
# ---------------------------------------------------------------------------


class HookStateOut(PlainModel):
    id: str
    name: str
    kind: Optional[str]
    state: str
    excuse: Optional[str]
    requires: Optional[Any]
    resolved_at: Optional[datetime]


def plot_state(model_registry: Any, requester_id: str, campaign_id: str) -> list[HookStateOut]:
    """Each of the campaign's hooks with its state: resolved, available, needs_check (a game-system
    check VTT decides) or blocked (with the GM's excuse). A hook with no requirement expression
    waits on all its dependency parents."""
    _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    hooks = _manager(model_registry, requester_id, HookManager).list(campaign_id=campaign_id) or []
    dependencies = _manager(model_registry, requester_id, HookDependencyManager)
    resolved = [str(hook.id) for hook in hooks if hook.resolved_at is not None]
    out: list[HookStateOut] = []
    for hook in hooks:
        requires = requirement_of(hook)
        if requires is None:
            parents = [str(edge.parent_hook_id) for edge in dependencies.list(child_hook_id=str(hook.id)) or []]
            requires = {"all": parents} if parents else None
        out.append(
            HookStateOut(
                id=str(hook.id),
                name=str(hook.name or ""),
                kind=hook.kind,
                state=hook_state(requires, resolved, hook.resolved_at is not None),
                excuse=hook.excuse,
                requires=requires,
                resolved_at=hook.resolved_at,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Templates (S4b, W7): a record made from a template, with its properties and tags
# ---------------------------------------------------------------------------

# What a copy never takes from its template: identity, scope, being a template, and what belongs to
# one play of it (a person's player, a hook's resolution).
_NOT_COPIED = {"id", "is_template", "campaign_id", "setting_id", "canon_level", "name", "user_id", "resolved_at", "resolved_journal_id"}


class TemplateUse(PlainModel):
    kind: str = Field(..., description="contract/wiki.json entity_types")
    template_id: str
    campaign_id: Optional[str] = None
    setting_id: Optional[str] = None
    name: Optional[str] = Field(None, description="The copy's name; the template's when not given")
    as_template: bool = Field(False, description="Make the copy a template itself (Save as template)")


class TemplateUseEnvelope(PlainModel):
    template: TemplateUse


class TemplateCopy(PlainModel):
    kind: str
    id: str
    name: str
    properties: int = Field(..., description="How many of its properties were copied")
    taxons: int = Field(..., description="How many of its tags and categories were copied")
    items: int = Field(0, description="How many of the item instances it carries were copied")


def instantiate(model_registry: Any, requester_id: str, use: TemplateUse) -> TemplateCopy:
    """A new record from ``use.template_id``: its fields and entry, its properties (record_metadata),
    its taxa and what it carries (each item instance made anew, carried by the copy, and owned by the
    copy where the template owned it), in the given campaign or setting under S6's rules. Anyone who
    can view a template copies it; the copy is the caller's. ``as_template`` copies any record one
    can view into a new template instead (Save as template), since a record never becomes one in
    place."""
    if use.kind not in MANAGER_OF_TYPE:
        raise HTTPException(status_code=422, detail=f"A template is one of: {', '.join(MANAGER_OF_TYPE)}")
    records = _manager(model_registry, requester_id, MANAGER_OF_TYPE[use.kind])
    source = records.get(id=use.template_id)
    if not use.as_template and not getattr(source, "is_template", None):
        raise HTTPException(status_code=422, detail="That record isn't a template")
    writable = set(records._model.Create.model_fields)
    fields = {name: value for name, value in source.model_dump().items() if name in writable and name not in _NOT_COPIED and value is not None}
    made = records.create(
        **fields,
        name=use.name or source.name,
        campaign_id=use.campaign_id,
        setting_id=use.setting_id,
        is_template=use.as_template or None,
    )
    copied_properties = 0
    if _serves(model_registry, "metadata"):
        from zephyrex.extensions.metadata.BLL_Metadata import RecordMetadataManager, RecordMetadataWrite

        properties = RecordMetadataManager(requester_id=requester_id, model_registry=model_registry)
        for row in properties.of_route(use.kind, str(source.id)).metadata:
            properties.add_route(
                RecordMetadataWrite(
                    target_entity_type=use.kind,
                    target_entity_id=str(made.id),
                    key=row.key,
                    value=row.value,
                    value_type=row.value_type,
                    ordinal=row.ordinal,
                    is_private=row.is_private,
                )
            )
            copied_properties += 1
    links = _manager(model_registry, requester_id, EntityTaxonManager)
    tags = links.list(target_entity_type=use.kind, target_entity_id=str(source.id)) or []
    for tag in tags:
        links.create(taxon_id=tag.taxon_id, target_entity_type=use.kind, target_entity_id=str(made.id))
    carried = _copy_inventory(model_registry, requester_id, use.kind, str(source.id), str(made.id))
    return TemplateCopy(
        kind=use.kind, id=str(made.id), name=str(made.name or ""), properties=copied_properties, taxons=len(tags), items=carried
    )


def _copy_inventory(model_registry: Any, requester_id: str, kind: str, source_id: str, copy_id: str) -> int:
    """What the template carries, carried by the copy: each item instance made anew (the same item,
    quantity and durability), owned by the copy where the template owned it."""
    holdings = _manager(model_registry, requester_id, EntityInventoryManager)
    instances = _manager(model_registry, requester_id, ItemInstanceManager)
    carried = holdings.list(target_entity_type=kind, target_entity_id=source_id) or []
    for holding in carried:
        original = instances.get(id=holding.item_instance_id)
        owner = original.owner_person_id
        fresh = instances.create(
            item_id=original.item_id,
            owner_person_id=copy_id if owner == source_id else owner,
            quantity=original.quantity,
            durability=original.durability,
        )
        holdings.create(item_instance_id=str(fresh.id), target_entity_type=kind, target_entity_id=copy_id, quantity=holding.quantity)
    return len(carried)


class TemplateManager(AbstractBLLManager[Any], RouterMixin):
    """REST for templates: POST /v1/template/instantiate."""

    prefix: ClassVar[str | None] = "/v1/template"
    tags: ClassVar[list[str] | None] = ["Templates"]
    routes_to_register: ClassVar[list[RouteType] | None] = []

    @custom_route(
        method="POST",
        path="/instantiate",
        input_model=TemplateUseEnvelope,
        output_model=TemplateCopy,
        authentication_type="jwt",
        status_code=201,
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Templates",),
        summary="A new record from a template, with its properties and tags (or a new template from a record)",
    )
    def instantiate_route(self, template: TemplateUse) -> TemplateCopy:
        return instantiate(self.model_registry, str(self.requester.id), TemplateUse.model_validate(template))


# ---------------------------------------------------------------------------
# Copy on start (operator, 2026-11-21): a scenario instantiated into a playthrough (Scenarios.py)
# ---------------------------------------------------------------------------

# The campaign's own records, in the order they're copied (a reference to a later one waits for the
# second pass).
_SCENARIO_RECORDS = (TaxonManager, StatusManager, LocationManager, FactionManager, PersonManager, ItemManager, JournalManager, HookManager)


def _scenario_links() -> list[tuple[Any, tuple[str, ...]]]:
    """Each link table, and the fields that tie a row to a copied record (any one is enough)."""
    from zephyrex.extensions.entity_posts.BLL_EntityPosts import EntityPostManager  # type: ignore[import-not-found]
    from zephyrex.extensions.genealogy.BLL_Genealogy import RelationshipManager
    from zephyrex.extensions.world_narrative.BLL_WorldNarrative import (  # type: ignore[import-not-found]
        DispositionManager,
        FactionHookManager,
        PersonHookManager,
        RelationInfluenceManager,
    )
    from zephyrex.extensions.world_taxonomy.BLL_WorldTaxonomy import EntityStatusManager  # type: ignore[import-not-found]

    return [
        (RelationshipManager, ("person_id", "faction_id", "target_person_id", "target_faction_id")),
        (RelationInfluenceManager, ("relationship_id",)),
        (HookDependencyManager, ("parent_hook_id", "child_hook_id")),
        (PersonHookManager, ("person_id",)),
        (FactionHookManager, ("faction_id",)),
        (DispositionManager, ("person_id",)),
        (EntityTaxonManager, ("target_entity_id",)),
        (EntityStatusManager, ("target_entity_id",)),
        (EntityPostManager, ("target_entity_id",)),
    ]


def instantiate_campaign(
    model_registry: Any,
    requester_id: str,
    source_campaign_id: str,
    name: Optional[str] = None,
    progress: Optional[Any] = None,
    pregens: Optional[list[str]] = None,
) -> CampaignStarted:
    """A playthrough of a scenario: a new campaign (its scenario_id the source's, its provenance the
    source's) with the requester's own copy of every record the scenario holds and every link
    between them, references turned to the copies (Scenarios.py). The setting's canon stays shared;
    templates stay with the scenario. ``pregens``, the setting's pregenerated characters the party
    picked, are copied in too (the setting's own stay untouched). Returns the campaign and the id
    map, source → copy."""
    from zephyrex.extensions.rpg_core.Scenarios import Copying, undo  # type: ignore[import-not-found]

    campaigns = _manager(model_registry, requester_id, CampaignManager)
    source = campaigns.get(id=source_campaign_id)
    picked = _pregen_rows(model_registry, requester_id, getattr(source, "setting_id", None), pregens or [])
    copying = Copying()
    try:
        made = _instantiate(model_registry, requester_id, campaigns, source, copying, name, progress or (lambda *_args: None), picked)
    except BaseException:
        # All or nothing: a start that fails partway leaves no half-copied campaign.
        undo(copying)
        raise
    _after_instantiate(model_registry, requester_id, str(source.id), str(made.id), dict(copying.id_map))
    return CampaignStarted(campaign=_manager(model_registry, requester_id, CampaignManager).get(id=str(made.id)).model_dump(mode="json"), id_map=copying.id_map)


# ---------------------------------------------------------------------------
# A campaign deleted takes its own records with it (Zephyrex RPG, 2026-11-22: deleted playthroughs
# left every record copied into them): its places, people, items, journals, hooks, tags and
# statuses, every link touching them, their properties and pictures, and its people's moves.
# ---------------------------------------------------------------------------

# Whether deleting a campaign removes its records (tests turn it off to leave orphans behind).
CASCADE_ON_DELETE = True


class RecordsRemoved(PlainModel):
    campaigns: list[str] = Field(..., description="The campaigns whose records were removed")
    removed: dict[str, int] = Field(..., description="How many of each were removed, by type")


def remove_campaign_records(model_registry: Any, requester_id: str, campaign_ids: list[str], dry_run: bool = False) -> RecordsRemoved:
    """Every record of ``campaign_ids`` removed, with the links, properties and pictures on them;
    links first, then the records, newest kind first (as a start's undo)."""
    from zephyrex.extensions.rpg_core.Scenarios import touching  # type: ignore[import-not-found]
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    removed: dict[str, int] = {}
    if not campaign_ids:
        return RecordsRemoved(campaigns=[], removed=removed)

    def drop(label: str, manager: Any, ids: list[str]) -> None:
        for one in dict.fromkeys(ids):
            if not dry_run:
                try:
                    manager.delete(id=one)
                except HTTPException:
                    continue
            removed[label] = removed.get(label, 0) + 1

    records: list[tuple[str, Any, list[str]]] = []
    for manager_class in _SCENARIO_RECORDS:
        manager = _manager(model_registry, requester_id, manager_class)
        rows = manager.list(filters=[FieldComparison(manager.Model, "campaign_id", "in", campaign_ids)]) or []
        records.append((manager_class.__name__.removesuffix("Manager").lower(), manager, [str(row.id) for row in rows]))
    record_ids = [one for _label, _manager_, ids in records for one in ids]
    if record_ids:
        for manager_class, anchors in _scenario_links():
            manager = _manager(model_registry, requester_id, manager_class)
            drop(manager_class.__name__.removesuffix("Manager").lower(), manager, [str(row.id) for row in touching(manager, anchors, record_ids)])
        holdings = _manager(model_registry, requester_id, EntityInventoryManager)
        drop("entityinventory", holdings, [str(row.id) for row in touching(holdings, ("target_entity_id",), record_ids)])
        instances = _manager(model_registry, requester_id, ItemInstanceManager)
        drop("iteminstance", instances, [str(row.id) for row in touching(instances, ("owner_person_id",), record_ids)])
        if _serves(model_registry, "metadata"):
            from zephyrex.extensions.metadata.BLL_Metadata import MetadataManager  # type: ignore[import-not-found]

            rows = MetadataManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)
            drop("property", rows, [str(row.id) for row in rows.list(filters=[FieldComparison(rows.Model, "target_entity_id", "in", record_ids)]) or []])
        if _serves(model_registry, "attachments"):
            from zephyrex.extensions.attachments.BLL_Attachments import AttachmentManager  # type: ignore[import-not-found]

            links = _manager(model_registry, requester_id, AttachmentManager)
            drop("attachment", links, [str(row.id) for row in touching(links, ("target_entity_id",), record_ids)])
    facts = _manager(model_registry, requester_id, KnownFactManager)
    drop("knownfact", facts, [str(row.id) for row in facts.list(filters=[FieldComparison(facts.Model, "campaign_id", "in", campaign_ids)]) or []])
    moves = _manager(model_registry, requester_id, PersonMoveManager)
    drop("personmove", moves, [str(row.id) for row in moves.list(filters=[FieldComparison(moves.Model, "campaign_id", "in", campaign_ids)]) or []])
    # A campaign's starts stay: a start is its starter's history (a failed start's undo deletes the
    # half-made playthrough, and the start must still say why).
    for label, manager, ids in reversed(records):
        drop(label, manager, ids)
    return RecordsRemoved(campaigns=sorted(campaign_ids), removed=removed)


def _every(manager: Any, filters: Optional[list[Any]] = None, page: int = 500) -> list[Any]:
    """Every row a list answers, page by page (a list answers one page)."""
    rows: list[Any] = []
    while True:
        found = manager.list(filters=filters, limit=page, offset=len(rows)) or []
        rows.extend(found)
        if len(found) < page:
            return rows


def remove_orphaned_records(model_registry: Any, requester_id: str, dry_run: bool = False) -> RecordsRemoved:
    """The requester's records whose campaign is gone (deleted before deleting took its records
    along), removed as remove_campaign_records does. A campaign counts as gone when it is the
    requester's own and they can't see it, or isn't there at all."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    live = {str(row.id) for row in _every(_manager(model_registry, requester_id, CampaignManager))}
    named: set[str] = set()
    for manager_class in _SCENARIO_RECORDS:
        manager = _manager(model_registry, requester_id, manager_class)
        # A record in a campaign that isn't live (NOT IN leaves out the campaign-free).
        wanted = [FieldComparison(manager.Model, "campaign_id", "not_in", sorted(live))] if live else [FieldComparison(manager.Model, "campaign_id", "ne", None)]
        named.update(str(row.campaign_id) for row in _every(manager, wanted) if getattr(row, "campaign_id", None))
    if not named:
        return RecordsRemoved(campaigns=[], removed={})
    # Gone: one of the requester's own campaigns they can no longer see (an owner always sees their
    # own live campaign), or one not there at all. Another's campaign is left alone. (ROOT's rows
    # don't say whether they're deleted.)
    root = CampaignManager(requester_id=env("ROOT_ID"), model_registry=model_registry)
    others = {str(row.id) for row in root.list(filters=[FieldComparison(root.Model, "id", "in", sorted(named))]) or [] if str(getattr(row, "created_by_user_id", "") or "") != str(requester_id)}
    # dry_run: what would go, counted, nothing deleted.
    return remove_campaign_records(model_registry, requester_id, sorted(named - others), dry_run=dry_run)


def _campaign_records_go(context: HookContext) -> None:
    """After a campaign is deleted, its records go too (as its deleter)."""
    if context.method_name != "delete" or not CASCADE_ON_DELETE:
        return
    campaign_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if not campaign_id:
        return
    from zephyrex.lib.Logging import logger

    try:
        remove_campaign_records(context.manager.model_registry, str(context.manager.requester.id), [str(campaign_id)])
    except Exception as error:  # noqa: BLE001 - the campaign is deleted either way; remove_orphaned_records finishes the job
        logger.warning(f"rpg_core: removing deleted campaign {campaign_id}'s records failed: {error}")


hook_bll(CampaignManager, timing=HookTiming.AFTER, priority=30)(_campaign_records_go)


# What other extensions do once a playthrough is made (VTT copies the scenario's scenes and tokens):
# each is called with (model_registry, requester_id, source_campaign_id, new_campaign_id, id_map),
# id_map every copied record's source id → copy id. A callback that fails is logged and the rest
# go on: the playthrough stands either way.
AFTER_INSTANTIATE: list[Callable[[Any, str, str, str, dict[str, str]], None]] = []


def _hook_key(hook: Any) -> tuple[str, str]:
    """A hook's name, as its module and qualified name: the same function imported again (an
    extension reloaded) is the same hook."""
    return (str(getattr(hook, "__module__", "")), str(getattr(hook, "__qualname__", repr(hook))))


def register_instantiate_hook(hook: Callable[[Any, str, str, str, dict[str, str]], None]) -> bool:
    """Add ``hook`` to AFTER_INSTANTIATE, called after each start with (model_registry,
    requester_id, source_campaign_id, new_campaign_id, id_map); a failing hook is logged and never
    undoes the start. The same hook again is not added twice: True when it was added."""
    if not callable(hook):
        raise HTTPException(status_code=422, detail="An instantiate hook is a function")
    key = _hook_key(hook)
    if any(held is hook or _hook_key(held) == key for held in AFTER_INSTANTIATE):
        return False
    AFTER_INSTANTIATE.append(hook)
    return True


def _after_instantiate(model_registry: Any, requester_id: str, source_campaign_id: str, new_campaign_id: str, id_map: dict[str, str]) -> None:
    from zephyrex.lib.Logging import logger

    for callback in list(AFTER_INSTANTIATE):
        try:
            callback(model_registry, requester_id, source_campaign_id, new_campaign_id, id_map)
        except Exception as error:  # noqa: BLE001 - another extension's failure never undoes the start
            logger.warning(f"rpg_core: an after-instantiate callback ({getattr(callback, '__qualname__', callback)}) failed for {new_campaign_id}: {error}")


PREGEN_TAG = "pregen"


def manager_classes_person(manager: Any) -> bool:
    return isinstance(manager, PersonManager)


def _pregen_ids(model_registry: Any, requester_id: str, setting_id: str) -> tuple[set[str], dict[str, list[str]]]:
    """The setting's canon pcs tagged Pregen (any kind of tag named so), and every record's tag names."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    taxa = {str(row.id): str(row.name) for row in _manager(model_registry, requester_id, TaxonManager).list(setting_id=setting_id) or []}
    pregen_taxa = [one for one, name in taxa.items() if name.strip().casefold() == PREGEN_TAG]
    links = _manager(model_registry, requester_id, EntityTaxonManager)
    tagged = {str(row.target_entity_id) for row in links.list(filters=[FieldComparison(links.Model, "taxon_id", "in", pregen_taxa)]) or [] if row.target_entity_type == "person"} if pregen_taxa else set()
    names: dict[str, list[str]] = {}
    if tagged:
        for row in links.list(filters=[FieldComparison(links.Model, "target_entity_id", "in", sorted(tagged))]) or []:
            if str(row.taxon_id) in taxa:
                names.setdefault(str(row.target_entity_id), []).append(taxa[str(row.taxon_id)])
    return tagged, names


def setting_pregens(model_registry: Any, requester_id: str, setting_id: str) -> SettingPregens:
    """The setting's pregenerated player characters (operator, 2026-11-21: setting-wide characters to
    pick from, a couple per class): its canon persons of kind pc tagged Pregen, by name."""
    _manager(model_registry, requester_id, SettingManager).get(id=setting_id)
    tagged, names = _pregen_ids(model_registry, requester_id, setting_id)
    people = [row for row in _manager(model_registry, requester_id, PersonManager).list(setting_id=setting_id) or [] if not row.campaign_id and row.kind == "pc" and str(row.id) in tagged]
    found = []
    for row in sorted(people, key=lambda one: str(one.name).casefold()):
        first = next((line for line in str(getattr(row, "description", "") or "").splitlines() if line.strip()), "")
        tags = sorted(names.get(str(row.id), []), key=lambda name: (name.casefold() != PREGEN_TAG, name.casefold()))
        found.append(SettingPregen(id=str(row.id), name=str(row.name), summary=summary(first), picture_url=getattr(row, "picture_url", None), tags=tags, source=getattr(row, "source", None)))
    return SettingPregens(pregens=found)


def _pregen_rows(model_registry: Any, requester_id: str, setting_id: Optional[str], ids: list[str]) -> list[Any]:
    """The picked pregens' rows: each must be a pregen of the scenario's setting (422 otherwise)."""
    if not ids:
        return []
    if not setting_id:
        raise HTTPException(status_code=422, detail="This scenario has no setting, so no pregens to pick from")
    tagged, _names = _pregen_ids(model_registry, requester_id, setting_id)
    people = _manager(model_registry, requester_id, PersonManager)
    rows = []
    for one in dict.fromkeys(ids):
        try:
            row = people.get(id=one)
        except HTTPException:
            row = None
        if row is None or row.campaign_id or str(getattr(row, "setting_id", "") or "") != str(setting_id) or one not in tagged:
            raise HTTPException(status_code=422, detail=f"{one} isn't one of this setting's pregens")
        rows.append(row)
    return rows


# A start's steps, in order, as its progress names them (each record kind, then the rest).
START_STEPS = (
    "copying tags",
    "copying statuses",
    "copying places",
    "copying organisations",
    "copying people",
    "copying items",
    "copying journals",
    "copying hooks",
    "copying relationships and links",
    "copying what they carry",
    "copying properties",
    "copying pictures",
    "finishing",
)


def _instantiate(model_registry: Any, requester_id: str, campaigns: Any, source: Any, copying: Any, name: Optional[str], progress: Any, picked: Optional[list[Any]] = None) -> Any:
    """instantiate_campaign's copy, each thing it makes recorded on ``copying`` (for undo).
    ``progress(step, done, campaign_id)`` is told each step as it starts (START_STEPS)."""
    from zephyrex.extensions.rpg_core.Scenarios import copy_rows, finish, touching  # type: ignore[import-not-found]

    source_campaign_id = str(source.id)
    gathered: list[tuple[Any, list[Any]]] = []
    for manager_class in _SCENARIO_RECORDS:
        manager = _manager(model_registry, requester_id, manager_class)
        rows = [row for row in manager.list(campaign_id=source_campaign_id) or [] if not getattr(row, "is_template", None)]
        gathered.append((manager, rows))
        copying.pending.update(str(row.id) for row in rows)
    copying.pending.update(str(row.id) for row in picked or [])
    # Every field the scenario has that a campaign takes on create (another extension's too: VTT's
    # game_system_id, so a playthrough's tests find their system), then its own name and lineage.
    writable = set(campaigns._model.Create.model_fields)
    carried = {key: value for key, value in source.model_dump().items() if key in writable and value is not None and key not in ("id", "user_id")}
    made = campaigns.create(**{**carried, "name": name or source.name, "is_scenario": False, "scenario_id": str(source.id)})
    # A field another extension makes settable only once a campaign exists, set the same way.
    updatable = set(getattr(campaigns._model, "Update").model_fields) - writable
    later = {key: value for key, value in source.model_dump().items() if key in updatable and value is not None and key not in ("id", "user_id", "name")}
    if later:
        made = campaigns.update(id=str(made.id), **later)
    copying.id_map[str(source.id)] = str(made.id)
    copying.made.append((campaigns, str(made.id)))
    for done, (manager, rows) in enumerate(gathered):
        progress(START_STEPS[done], done, str(made.id))
        copy_rows(manager, rows, copying)
        if manager_classes_person(manager) and picked:
            # The party's pregens: the setting's characters, now the playthrough's own.
            copy_rows(manager, picked, copying, fixed={"campaign_id": str(made.id), "setting_id": None})
    step = len(gathered)
    progress(START_STEPS[step], step, str(made.id))
    record_ids = [one for one in copying.id_map if one != str(source.id)]
    for manager_class, anchors in _scenario_links():
        manager = _manager(model_registry, requester_id, manager_class)
        # The scenario's own id too: its play-style tags come with it.
        rows = touching(manager, anchors, list(copying.id_map))
        copying.pending.update(str(row.id) for row in rows)
        copy_rows(manager, rows, copying)
    progress(START_STEPS[step + 1], step + 1, str(made.id))
    _copy_carried(model_registry, requester_id, record_ids, copying, copy_rows, touching)
    _copy_record_extras(model_registry, requester_id, record_ids, copying, lambda offset: progress(START_STEPS[step + 2 + offset], step + 2 + offset, str(made.id)))
    progress(START_STEPS[step + 4], step + 4, str(made.id))
    finish(copying)
    return made


# Whether a start's copy runs in a background thread (each manager call its own session, so a
# thread is sound: Zephyrex Server's probe, server-framework 6dc40a64). Its stalls on the runner
# were the test database on NFS, not the thread: with it on local disk the polled start is quick.
# False copies before answering (the start comes back done), as lite does.
START_IN_BACKGROUND = True


def start_campaign(model_registry: Any, requester_id: str, source_campaign_id: str, name: Optional[str] = None, pregens: Optional[list[str]] = None) -> CampaignStartAccepted:
    """instantiate_campaign in the background, under the requester: answered at once with the
    start (state running), its row updated at each step (and published to the scenario's room), and
    done with the playthrough and its id map, or failed with why (the copy undone)."""
    import contextvars
    import json
    import threading

    # The scenario must be the requester's to read, and the pregens its setting's, before anything
    # starts (404, 422 otherwise).
    scenario = _manager(model_registry, requester_id, CampaignManager).get(id=source_campaign_id)
    _pregen_rows(model_registry, requester_id, getattr(scenario, "setting_id", None), pregens or [])
    starts = _manager(model_registry, requester_id, CampaignStartManager)
    row = starts.create(scenario_id=source_campaign_id, name=name, state="running", done=0, total=len(START_STEPS), step=START_STEPS[0])
    start_id = str(row.id)

    def report(step: str, done: int, campaign_id: str) -> None:
        _manager(model_registry, requester_id, CampaignStartManager).update(id=start_id, step=step, done=done, campaign_id=campaign_id)

    def run() -> None:
        # The finished request's deadline came with its context: the copy has its own time.
        from zephyrex.lib.RequestContext import set_request_deadline_ms

        set_request_deadline_ms(None)
        try:
            started = instantiate_campaign(model_registry, requester_id, source_campaign_id, name, progress=report, pregens=pregens)
        except Exception as error:  # noqa: BLE001 - the start's row says why; the copy was undone
            detail = getattr(error, "detail", None) or str(error) or type(error).__name__
            _manager(model_registry, requester_id, CampaignStartManager).update(id=start_id, state="failed", error=str(detail))
            return
        _manager(model_registry, requester_id, CampaignStartManager).update(
            id=start_id,
            state="done",
            done=len(START_STEPS),
            step="done",
            campaign_id=str(started.campaign["id"]),
            id_map=json.dumps(started.id_map),
        )

    if not START_IN_BACKGROUND:
        # For now the copy runs before the answer (about 8 s for 120 records with their properties
        # and pictures); the start comes back done, as lite's does, in the same shapes.
        run()
        return CampaignStartAccepted(start=_manager(model_registry, requester_id, CampaignStartManager).get(id=start_id).model_dump(mode="json"))
    # Under the request's own context (its user, tenant and read-replica state), as the copy would
    # run in the request itself; a bare thread starts without them.
    context = contextvars.copy_context()
    threading.Thread(target=context.run, args=(run,), name=f"campaign-start-{start_id}", daemon=True).start()
    return CampaignStartAccepted(start=row.model_dump(mode="json"))


def _copy_carried(model_registry: Any, requester_id: str, record_ids: list[str], copying: Any, copy_rows: Any, touching: Any) -> None:
    """What the copied records carry: each item instance they hold or own made anew, then held."""
    holdings = _manager(model_registry, requester_id, EntityInventoryManager)
    instances = _manager(model_registry, requester_id, ItemInstanceManager)
    held = touching(holdings, ("target_entity_id",), record_ids)
    owned = touching(instances, ("owner_person_id",), record_ids)
    wanted = {str(row.item_instance_id) for row in held} - {str(row.id) for row in owned}
    extra = touching(instances, ("id",), sorted(wanted)) if wanted else []
    copy_rows(instances, owned + extra, copying)
    copy_rows(holdings, held, copying)


def _copy_record_extras(model_registry: Any, requester_id: str, record_ids: list[str], copying: Any, at: Any = lambda _offset: None) -> None:
    """Each copied record's properties and pictures (the same uploaded assets, attached again), one
    plural create each. Properties are stored as SYSTEM, as RecordMetadataManager.add_route stores
    them; its checks hold by construction (the requester made the records just now, and each copy's
    keys are its source's, so unique and within the limit), so the rows go in one create."""
    from zephyrex.extensions.rpg_core.Scenarios import copy_rows, create_all, touching  # type: ignore[import-not-found]
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    at(0)
    if _serves(model_registry, "metadata") and record_ids:
        from zephyrex.extensions.metadata.BLL_Metadata import MetadataManager  # type: ignore[import-not-found]

        rows = MetadataManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)
        held = rows.list(filters=[FieldComparison(rows.Model, "target_entity_id", "in", record_ids)]) or []
        if held:
            made = create_all(
                rows,
                [
                    {
                        "target_entity_type": row.target_entity_type,
                        "target_entity_id": copying.id_map[str(row.target_entity_id)],
                        "key": row.key,
                        "value": row.value,
                        "value_type": row.value_type,
                        "ordinal": row.ordinal,
                        "is_private": row.is_private,
                    }
                    for row in held
                ],
            )
            copying.made.extend((rows, str(one.id)) for one in made)
    at(1)
    if _serves(model_registry, "attachments") and record_ids:
        from zephyrex.extensions.attachments.BLL_Attachments import AttachmentManager  # type: ignore[import-not-found]

        links = _manager(model_registry, requester_id, AttachmentManager)
        # One plural create (server-framework a9ef4366 checks each and writes all or none).
        copy_rows(links, touching(links, ("target_entity_id",), record_ids), copying)


# ---------------------------------------------------------------------------
# A campaign's room (the framework's rooms): its changes reach whoever has it open, and VTT puts a
# campaign's scenes and tables in the same room, so their lists update live. Joining needs VIEW on
# the campaign (its GM and players). Nothing happens unless the app loads `rooms`.
# ---------------------------------------------------------------------------

room_of(CampaignManager, lambda campaign: ("campaign", campaign.id))
# A start's progress reaches the scenario's room (polling GET /v1/campaign_start/{id} is the fallback).
room_of(CampaignStartManager, lambda start: ("campaign", start.scenario_id))


# POST /v1/campaign/{id}/lore_search (LoreSearch.py), attached as matching is.
def _attach_lore_search() -> None:
    from zephyrex.extensions.rpg_core.LoreSearch import LoreSearchEnvelope, LoreSearched, lore_search  # type: ignore[import-not-found]

    @custom_route(
        method="POST",
        path="/{id}/lore_search",
        input_model=LoreSearchEnvelope,
        output_model=LoreSearched,
        authentication_type="jwt",
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="The campaign's lore passages for a text: exact names first, then full-text, trigram and vector ranks fused, to a token budget",
    )
    def lore_search_route(self: Any, id: str, lore_search: Any) -> Any:
        from zephyrex.extensions.rpg_core.LoreSearch import LoreSearchAsk, lore_search as search  # type: ignore[import-not-found]

        asked = LoreSearchAsk.model_validate(lore_search)
        return search(self.model_registry, str(self.requester.id), id, asked.text, asked.k, asked.token_budget, asked.kinds, asked.tags, asked.include_setting)

    CampaignManager.lore_search_route = lore_search_route  # type: ignore[attr-defined]


_attach_lore_search()


# POST /v1/campaign/card_person (CardPerson.py): a character card as a person to chat with.
def _attach_card_person() -> None:
    from zephyrex.extensions.rpg_core.CardPerson import CardEnvelope, CardPersonImported  # type: ignore[import-not-found]

    @custom_route(
        method="POST",
        path="/card_person",
        input_model=CardEnvelope,
        output_model=CardPersonImported,
        authentication_type="jwt",
        status_code=201,
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="A character card as a person of the requester's Characters campaign, to chat with outside any scenario",
    )
    def card_person_route(self: Any, card: Any) -> Any:
        from zephyrex.extensions.rpg_core.CardPerson import CardAsk, import_card_person  # type: ignore[import-not-found]

        return import_card_person(self.model_registry, str(self.requester.id), CardAsk.model_validate(card).model_dump())

    CampaignManager.card_person_route = card_person_route  # type: ignore[attr-defined]


_attach_card_person()
