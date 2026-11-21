# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_taxonomy models (W6): the same resources, fields and rules as the lite edition's
(client/src/lib/worldRecords.ts). OBJECT_PLAN §3's world_taxonomy, without property kits (S4b).

- ``/v1/taxon``: a tag, category, race, species, creature type, culture, ethnicity, language
  family, religion, condition type or material type (``kind`` from contract/wiki.json), in a tree
  (``parent_id``; a cycle is refused), with a colour (#rrggbb).
- ``/v1/entity_taxon``: a taxon on any record (``target_entity_type`` from the contract's
  entity_types, ``target_entity_id``); once per taxon and record.
- ``/v1/status``: a status (entity_status or quest_status) with a colour.
- ``/v1/entity_status``: a record's status; one per record.

Polymorphic links, as entity_posts' posts, so this Tier 1 extension depends on no other world
extension. The campaign link on taxa and statuses is rpg_core's.
"""

from typing import Any, Callable, ClassVar, Optional, Type

from fastapi import HTTPException
from pydantic import Field, field_validator
from zephyrex.extensions.wiki_shared.Contract import ENTITY_TYPES, STATUS_KINDS, TAGGABLE_TYPES, TAXON_KINDS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import (  # type: ignore[import-not-found]
    checked_colour,
    checked_kind,
    checked_name,
    refuse_parent_cycle,
)
from zephyrex.logic.AbstractLogicManager import (
    AbstractBLLManager,
    ApplicationModel,
    DescriptionMixinModel,
    HookContext,
    HookTiming,
    ModelMeta,
    NameMixinModel,
    ParentMixinModel,
    StringSearchModel,
    UpdateMixinModel,
    hook_bll,
)
from zephyrex.pydantic2.fastapi import RouterMixin

# The framework's registry BaseModel, which it re-exports without declaring it.
from zephyrex.pydantic2.registry import BaseModel  # type: ignore[attr-defined]


def _taxon_kind(value: Any) -> Any:
    return checked_kind(value, TAXON_KINDS, "taxon")


def _status_kind(value: Any) -> Any:
    return checked_kind(value, STATUS_KINDS, "status")


def _entity_type(value: Any) -> Any:
    if value not in ENTITY_TYPES:
        raise ValueError(f"A target is one of: {', '.join(ENTITY_TYPES)}")
    return value


def _taggable_type(value: Any) -> Any:
    """A taxon tags any record, and a campaign too (a scenario's play-style tags)."""
    if value not in TAGGABLE_TYPES:
        raise ValueError(f"A target is one of: {', '.join(TAGGABLE_TYPES)}")
    return value


class TaxonModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    ParentMixinModel.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["TaxonManager"]] = None
    kind: Optional[str] = Field(None, description="contract/wiki.json taxon_kinds")
    colour: Optional[str] = Field(None, description="#rrggbb")
    table_comment: ClassVar[str] = "A tag, category, race, species, culture, religion or other classification, in a tree."

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        parent_id: Optional[str] = None
        kind: Optional[str] = None
        colour: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_taxon_kind)
        _colour = field_validator("colour")(checked_colour)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        parent_id: Optional[str] = None
        kind: Optional[str] = None
        colour: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_taxon_kind)
        _colour = field_validator("colour")(checked_colour)

    class Search(ApplicationModel.Search):
        name: Optional[StringSearchModel] = None
        kind: Optional[StringSearchModel] = None
        parent_id: Optional[StringSearchModel] = None


class TaxonManager(AbstractBLLManager, RouterMixin):
    _model = TaxonModel


TaxonModel.Manager = TaxonManager


class EntityTaxonModel(ApplicationModel.Optional, UpdateMixinModel.Optional, TaxonModel.Reference.Optional, metaclass=ModelMeta):
    Manager: ClassVar[Type["EntityTaxonManager"]] = None
    target_entity_type: Optional[str] = Field(None, description="contract/wiki.json taggable_types")
    target_entity_id: Optional[str] = Field(None, description="The tagged record's id")
    table_comment: ClassVar[str] = "A taxon on a record (polymorphic); once per taxon and record."

    class Create(BaseModel, TaxonModel.Reference.ID):
        target_entity_type: str = Field(...)
        target_entity_id: str = Field(...)

        _type = field_validator("target_entity_type")(_taggable_type)

    class Update(BaseModel):
        pass

    class Search(ApplicationModel.Search, TaxonModel.Reference.ID.Search):
        target_entity_type: Optional[StringSearchModel] = None
        target_entity_id: Optional[StringSearchModel] = None


class EntityTaxonManager(AbstractBLLManager, RouterMixin):
    _model = EntityTaxonModel


EntityTaxonModel.Manager = EntityTaxonManager


class StatusModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["StatusManager"]] = None
    kind: Optional[str] = Field(None, description="contract/wiki.json status_kinds")
    colour: Optional[str] = Field(None, description="#rrggbb")
    table_comment: ClassVar[str] = "A status a record can be in (alive, destroyed, open, resolved…)."

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        kind: Optional[str] = None
        colour: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_status_kind)
        _colour = field_validator("colour")(checked_colour)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        kind: Optional[str] = None
        colour: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_status_kind)
        _colour = field_validator("colour")(checked_colour)

    class Search(ApplicationModel.Search):
        name: Optional[StringSearchModel] = None
        kind: Optional[StringSearchModel] = None


class StatusManager(AbstractBLLManager, RouterMixin):
    _model = StatusModel


StatusModel.Manager = StatusManager


class EntityStatusModel(ApplicationModel.Optional, UpdateMixinModel.Optional, StatusModel.Reference.Optional, metaclass=ModelMeta):
    Manager: ClassVar[Type["EntityStatusManager"]] = None
    target_entity_type: Optional[str] = Field(None, description="contract/wiki.json entity_types")
    target_entity_id: Optional[str] = Field(None, description="The record's id")
    table_comment: ClassVar[str] = "A record's status (polymorphic); one per record."

    class Create(BaseModel, StatusModel.Reference.ID):
        target_entity_type: str = Field(...)
        target_entity_id: str = Field(...)

        _type = field_validator("target_entity_type")(_entity_type)

    class Update(BaseModel, StatusModel.Reference.ID):
        pass

    class Search(ApplicationModel.Search, StatusModel.Reference.ID.Search):
        target_entity_type: Optional[StringSearchModel] = None
        target_entity_id: Optional[StringSearchModel] = None


class EntityStatusManager(AbstractBLLManager, RouterMixin):
    _model = EntityStatusModel


EntityStatusModel.Manager = EntityStatusManager


@hook_bll(TaxonManager, timing=HookTiming.BEFORE, priority=10)
def _taxon_no_cycle(context: HookContext) -> None:
    """A taxon can't sit under itself or under one of its own descendants."""
    refuse_parent_cycle(context, "taxon")


def _once_per(fields: tuple[str, ...], detail: str) -> Callable[[HookContext], None]:
    def check(context: HookContext) -> None:
        if context.method_name != "create":
            return
        wanted = {field: context.kwarg(field, default=None) for field in fields}
        if all(wanted.values()) and context.manager.list(**wanted):
            raise HTTPException(status_code=422, detail=detail)

    return check


hook_bll(EntityTaxonManager, timing=HookTiming.BEFORE, priority=10)(
    _once_per(("taxon_id", "target_entity_type", "target_entity_id"), "That record already has that taxon")
)
hook_bll(EntityStatusManager, timing=HookTiming.BEFORE, priority=10)(
    _once_per(("target_entity_type", "target_entity_id"), "That record already has a status: change it instead")
)


@hook_bll(TaxonManager, timing=HookTiming.AFTER, priority=10)
def _taxon_takes_its_links(context: HookContext) -> None:
    """Deleting a taxon takes it off every record."""
    _delete_links(context, EntityTaxonManager, "taxon_id")


@hook_bll(StatusManager, timing=HookTiming.AFTER, priority=10)
def _status_takes_its_links(context: HookContext) -> None:
    """Deleting a status clears it from every record that had it."""
    _delete_links(context, EntityStatusManager, "status_id")


def _delete_links(context: HookContext, manager_class: Any, field: str) -> None:
    if context.method_name != "delete":
        return
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if not record_id:
        return
    manager = manager_class(requester_id=context.manager.requester.id, model_registry=context.manager.model_registry)
    for row in manager.list(**{field: record_id}) or []:
        manager.delete(id=row.id)


__all__ = ["TaxonModel", "EntityTaxonModel", "StatusModel", "EntityStatusModel"]
