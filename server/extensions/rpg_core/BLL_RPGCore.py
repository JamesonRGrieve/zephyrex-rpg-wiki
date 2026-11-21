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

from datetime import datetime
from typing import Any, ClassVar, Optional, Type

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
from zephyrex.extensions.wiki_shared.Names import names_text, stored_names, stored_voice, voice_text  # type: ignore[import-not-found]
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


class SettingManager(AbstractBLLManager, RouterMixin):
    _model = SettingModel


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


class CampaignStartEnvelope(PlainModel):
    instantiate: CampaignStart


class CampaignStarted(PlainModel):
    campaign: dict[str, Any] = Field(..., description="The new campaign, a playthrough of the scenario")
    id_map: dict[str, str] = Field(..., description="Each copied record's id (and the scenario's) → its copy's")


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
        output_model=CampaignStarted,
        authentication_type="jwt",
        status_code=201,
        expose_in=(ExposeIn.REST,),
        openapi_tags=("Campaigns",),
        summary="Start a scenario: a new campaign with its own copy of every record and relation",
    )
    def instantiate_route(self, id: str, instantiate: CampaignStart) -> CampaignStarted:
        start = CampaignStart.model_validate(instantiate)
        return instantiate_campaign(self.model_registry, str(self.requester.id), id, start.name)

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
) -> list[WorldEntity]:
    """The changes matching ``filters`` for each kind, past the cursor; with ``canon_only``, only
    records with no campaign (a setting's canon)."""
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
    if "attachments" not in model_registry.loaded_extension_names() or not shown:
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
    if "metadata" not in model_registry.loaded_extension_names() or not ids:
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
        found += _gather(model_registry, requester_id, wanted, {"setting_id": setting_id}, True, start, floor, limit)
    return _paged(found, limit, model_registry, requester_id)


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


class PersonMoved(PlainModel):
    person_id: str
    from_location_id: Optional[str] = Field(None, alias="from")
    to_location_id: str = Field(..., alias="to")
    at: Optional[CampaignClock] = Field(None, description="The campaign's clock when they moved")
    reason: Optional[str] = None

    model_config = {"populate_by_name": True}


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
    if "metadata" in model_registry.loaded_extension_names():
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


def instantiate_campaign(model_registry: Any, requester_id: str, source_campaign_id: str, name: Optional[str] = None) -> CampaignStarted:
    """A playthrough of a scenario: a new campaign (its scenario_id the source's, its provenance the
    source's) with the requester's own copy of every record the scenario holds and every link
    between them, references turned to the copies (Scenarios.py). The setting's canon stays shared;
    templates stay with the scenario. Returns the campaign and the id map, source → copy."""
    from zephyrex.extensions.rpg_core.Scenarios import Copying, undo  # type: ignore[import-not-found]

    campaigns = _manager(model_registry, requester_id, CampaignManager)
    source = campaigns.get(id=source_campaign_id)
    copying = Copying()
    try:
        made = _instantiate(model_registry, requester_id, campaigns, source, copying, name)
    except BaseException:
        # All or nothing: a start that fails partway leaves no half-copied campaign.
        undo(copying)
        raise
    return CampaignStarted(campaign=_manager(model_registry, requester_id, CampaignManager).get(id=str(made.id)).model_dump(mode="json"), id_map=copying.id_map)


def _instantiate(model_registry: Any, requester_id: str, campaigns: Any, source: Any, copying: Any, name: Optional[str]) -> Any:
    """instantiate_campaign's copy, each thing it makes recorded on ``copying`` (for undo)."""
    from zephyrex.extensions.rpg_core.Scenarios import copy_rows, finish, touching  # type: ignore[import-not-found]

    source_campaign_id = str(source.id)
    gathered: list[tuple[Any, list[Any]]] = []
    for manager_class in _SCENARIO_RECORDS:
        manager = _manager(model_registry, requester_id, manager_class)
        rows = [row for row in manager.list(campaign_id=source_campaign_id) or [] if not getattr(row, "is_template", None)]
        gathered.append((manager, rows))
        copying.pending.update(str(row.id) for row in rows)
    made = campaigns.create(
        name=name or source.name,
        description=source.description,
        setting_id=source.setting_id,
        provenance=getattr(source, "provenance", None),
        source=getattr(source, "source", None),
        is_scenario=False,
        scenario_id=str(source.id),
    )
    copying.id_map[str(source.id)] = str(made.id)
    copying.made.append((campaigns, str(made.id)))
    for manager, rows in gathered:
        copy_rows(manager, rows, copying)
    record_ids = [one for one in copying.id_map if one != str(source.id)]
    for manager_class, anchors in _scenario_links():
        manager = _manager(model_registry, requester_id, manager_class)
        # The scenario's own id too: its play-style tags come with it.
        rows = touching(manager, anchors, list(copying.id_map))
        copying.pending.update(str(row.id) for row in rows)
        copy_rows(manager, rows, copying)
    _copy_carried(model_registry, requester_id, record_ids, copying, copy_rows, touching)
    _copy_record_extras(model_registry, requester_id, record_ids, copying)
    finish(copying)
    return made


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


def _copy_record_extras(model_registry: Any, requester_id: str, record_ids: list[str], copying: Any) -> None:
    """Each copied record's properties and pictures (the same uploaded assets, attached again)."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    loaded = model_registry.loaded_extension_names()
    if "metadata" in loaded and record_ids:
        from zephyrex.extensions.metadata.BLL_Metadata import (  # type: ignore[import-not-found]
            MetadataManager,
            RecordMetadataManager,
            RecordMetadataWrite,
        )

        rows = MetadataManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)
        writer = RecordMetadataManager(requester_id=requester_id, model_registry=model_registry)
        for row in rows.list(filters=[FieldComparison(rows.Model, "target_entity_id", "in", record_ids)]) or []:
            writer.add_route(
                RecordMetadataWrite(
                    target_entity_type=row.target_entity_type,
                    target_entity_id=copying.id_map[str(row.target_entity_id)],
                    key=row.key,
                    value=row.value,
                    value_type=row.value_type,
                    ordinal=row.ordinal,
                    is_private=row.is_private,
                )
            )
    if "attachments" in loaded and record_ids:
        from zephyrex.extensions.attachments.BLL_Attachments import AttachmentManager  # type: ignore[import-not-found]

        links = _manager(model_registry, requester_id, AttachmentManager)
        from zephyrex.extensions.rpg_core.Scenarios import copy_rows, touching  # type: ignore[import-not-found]

        # Attachments refuse plural creates: each picture attached on its own.
        copy_rows(links, touching(links, ("target_entity_id",), record_ids), copying, one_at_a_time=True)


# ---------------------------------------------------------------------------
# A campaign's room (the framework's rooms): its changes reach whoever has it open, and VTT puts a
# campaign's scenes and tables in the same room, so their lists update live. Joining needs VIEW on
# the campaign (its GM and players). Nothing happens unless the app loads `rooms`.
# ---------------------------------------------------------------------------

room_of(CampaignManager, lambda campaign: ("campaign", campaign.id))
