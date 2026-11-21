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
from zephyrex.extensions.wiki_shared.Contract import PERSON_KINDS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import (  # type: ignore[import-not-found]
    checked_kind,
    checked_name,
    with_entry_text,
)
from zephyrex.extensions.wiki_shared.Contract import ENTITY_TYPES, LIMITS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Report import report_entry  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Summary import summary  # type: ignore[import-not-found]
from zephyrex.extensions.world_inventory.BLL_WorldInventory import ItemManager, ItemModel  # type: ignore[import-not-found]
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
    StatusManager,
    StatusModel,
    TaxonManager,
    TaxonModel,
)
from zephyrex.extensions.world_social.BLL_WorldSocial import FactionManager, FactionModel  # type: ignore[import-not-found]
from zephyrex.extensions.world_spatial.BLL_WorldSpatial import LocationManager, LocationModel  # type: ignore[import-not-found]
from zephyrex.logic.AbstractLogicManager import (
    AbstractBLLManager,
    ApplicationModel,
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
from zephyrex.logic.BLL_Auth import UserModel
from zephyrex.pydantic2.fastapi import RouterMixin
from zephyrex.pydantic2.fastapi.types import RouteType

# The framework's registry BaseModel, which it re-exports without declaring it.
from zephyrex.pydantic2.registry import BaseModel  # type: ignore[attr-defined]
from zephyrex.pydantic2.sqlalchemy import extension_model


class CampaignModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    UserModel.Reference.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["CampaignManager"]] = None
    table_comment: ClassVar[str] = "A world: the top-level container every record scopes to. user_id = its owner."

    class Create(BaseModel, UserModel.Reference.ID.Optional):
        name: str = Field(...)
        description: Optional[str] = None

        _name = field_validator("name")(checked_name)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None

        _name = field_validator("name")(checked_name)

    class Search(ApplicationModel.Search, UserModel.Reference.ID.Search):
        name: Optional[StringSearchModel] = None


class CampaignManager(AbstractBLLManager, RouterMixin):
    _model = CampaignModel


CampaignModel.Manager = CampaignManager


def _person_kind(value: Any) -> Any:
    return checked_kind(value, PERSON_KINDS, "person")


@extension_model(PersonModel)
class RPG_PersonModel(BaseModel):
    """genealogy's Person as the character table: kind, campaign, player, place and entry."""

    kind: Optional[str] = Field(None, description="contract/wiki.json person_kinds")
    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = a template")
    user_id: Optional[str] = Field(None, description="FK → users.id; the player. None = an NPC")
    location_id: Optional[str] = Field(None, description="FK → locations.id; where they are")
    entry: Optional[str] = Field(None, description="The entry: a Plate value as JSON text")

    class Create(BaseModel):
        kind: Optional[str] = None
        campaign_id: Optional[str] = None
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
        user_id: Optional[StringSearchModel] = None
        location_id: Optional[StringSearchModel] = None


@extension_model(LocationModel)
class RPG_LocationModel(BaseModel):
    """A location's campaign: rpg_core scopes Tier 1 records, never the reverse."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")

    class Create(BaseModel):
        campaign_id: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None


@extension_model(FactionModel)
class RPG_FactionModel(BaseModel):
    """A faction's campaign: rpg_core scopes Tier 1 records, never the reverse."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")

    class Create(BaseModel):
        campaign_id: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None


@extension_model(ItemModel)
class RPG_ItemModel(BaseModel):
    """An item's campaign: rpg_core scopes Tier 1 records, never the reverse. Its rule system is
    zephyrex-vtt's rpg_systems' to add (game_systems moved there; operator, 2026-11-20)."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")

    class Create(BaseModel):
        campaign_id: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None


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


for _manager in (PersonManager, LocationManager, FactionManager, ItemManager, JournalManager, HookManager, TaxonManager, StatusManager):
    hook_bll(_manager, timing=HookTiming.BEFORE, priority=20)(_world_stays)



@extension_model(JournalModel)
class RPG_JournalModel(BaseModel):
    """A journal's campaign: rpg_core scopes Tier 1 records, never the reverse."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")

    class Create(BaseModel):
        campaign_id: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None


@extension_model(HookModel)
class RPG_HookModel(BaseModel):
    """A hook's campaign. Hooks stay out of world_entities: plot hooks are often GM secrets (W9)."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")

    class Create(BaseModel):
        campaign_id: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None


class _Campaign(BaseModel):
    """A taxonomy record's campaign: none = shared across campaigns (a tag set reused everywhere)."""

    campaign_id: Optional[str] = Field(None, description="FK → campaigns.id; none = shared across campaigns")

    class Create(BaseModel):
        campaign_id: Optional[str] = None

    class Update(BaseModel):
        campaign_id: Optional[str] = None

    class Search(BaseModel):
        campaign_id: Optional[StringSearchModel] = None


@extension_model(TaxonModel)
class RPG_TaxonModel(_Campaign):
    """A taxon's campaign."""


@extension_model(StatusModel)
class RPG_StatusModel(_Campaign):
    """A status's campaign."""


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
# {id, kind, name, aliases, summary, picture, updated_at, deleted}, paged by (changed_at, id).
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


def world_entities(
    model_registry: Any,
    requester_id: str,
    campaign_id: str,
    since: Optional[datetime] = None,
    kinds: Optional[list[str]] = None,
    after: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> WorldEntitiesPage:
    """One page of the campaign's changed entities, oldest first, and the cursor for the next."""
    if not 1 <= limit <= MAX_LIMIT:
        raise HTTPException(status_code=422, detail=f"limit is 1 to {MAX_LIMIT}")
    wanted = kinds or list(WORLD_ENTITY_MANAGERS)
    unknown = [kind for kind in wanted if kind not in WORLD_ENTITY_MANAGERS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown kinds: {', '.join(unknown)}")
    _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    floor = _read_cursor(after) if after else None
    start = _naive(since) if since else None
    if floor and (start is None or floor[0] > start):
        start = floor[0]
    found: list[WorldEntity] = []
    for kind in wanted:
        manager = _manager(model_registry, requester_id, WORLD_ENTITY_MANAGERS[kind])
        taken, page_after = 0, None
        while taken <= limit:
            page = manager.changes(since=start, after=page_after, limit=limit + 1, campaign_id=campaign_id)
            for change in page.changes:
                record = change.record
                entity = WorldEntity(
                    id=str(record.id),
                    kind=kind,
                    name=str(record.name or ""),
                    aliases=[],
                    summary=summary(getattr(record, "description", None)),
                    picture=None,
                    updated_at=_naive(change.changed_at),
                    deleted=change.deleted_at is not None,
                )
                if floor and (entity.updated_at, entity.id) <= floor:
                    continue
                found.append(entity)
                taken += 1
            if not page.next:
                break
            page_after = page.next
    found.sort(key=lambda entity: (entity.updated_at, entity.id))
    shown = found[:limit]
    return WorldEntitiesPage(world_entities=shown, next=_cursor_of(shown[-1]) if len(found) > limit else None)


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
        summary="A campaign's places, people, factions, items and journals changed since a time, tombstones included",
    )
    def list_route(
        self,
        campaign_id: str,
        since: Optional[datetime] = None,
        kinds: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> WorldEntitiesPage:
        return world_entities(
            self.model_registry,
            str(self.requester.id),
            campaign_id,
            since=since,
            kinds=[kind for kind in kinds.split(",") if kind] if kinds else None,
            after=after,
            limit=limit,
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
