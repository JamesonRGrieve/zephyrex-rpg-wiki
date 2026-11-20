# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_spatial models: a location tree, the same resource, fields and rules as the lite
edition's (client/src/lib/locationRecords.ts).

``/v1/location``: a place at any scale (``kind`` from contract/wiki.json), under its parent. A place
can belong to a person (``associated_person_id``): their equipment slots, body and body parts. What
someone wears or wields is an item instance whose location is one of their equipment_slot or
body_part places; carried anywhere else, it's packed (OBJECT_PLAN §4; zephyrex-vtt's checks). Its
entry is a Plate value; its description is the entry's plain-text copy, for search (wiki_shared/Entry.py).
Ported from zephyrex-vtt's rpg_state.LocationModel with the same table and field names
(OBJECT_PLAN §6). The campaign link is rpg_core's (it injects ``campaign_id``), so this tier
stays campaign-free. A parent change that would close a cycle is refused.
"""

from typing import Any, ClassVar, Optional, Type

from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.genealogy.BLL_Genealogy import PersonModel
from zephyrex.extensions.wiki_shared.Contract import LOCATION_KINDS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import (  # type: ignore[import-not-found]
    checked_kind,
    checked_name,
    refuse_parent_cycle,
    with_entry_text,
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


class LocationModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    ParentMixinModel.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["LocationManager"]] = None
    kind: Optional[str] = Field(None, description="contract/wiki.json location_kinds")
    entry: Optional[str] = Field(None, description="The entry: a Plate value as JSON text")
    associated_person_id: Optional[str] = Field(
        None, description="The person this place belongs to: an equipment slot, a body or a body part"
    )
    table_comment: ClassVar[str] = (
        "A place at any scale, under its parent (parent_id). entry is a Plate value; description "
        "is its plain-text copy, for search. associated_person_id binds a place to a person: an "
        "equipment_slot or body_part bound to someone is where what they wear or wield sits, so "
        "equipping is a move (OBJECT_PLAN §4)."
    )

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        entry: Optional[Any] = None
        parent_id: Optional[str] = None
        kind: Optional[str] = None
        associated_person_id: Optional[str] = None

        _name = field_validator("name")(checked_name)

        @field_validator("kind")
        @classmethod
        def _kind(cls, value: Any) -> Any:
            return checked_kind(value, LOCATION_KINDS, "location")

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        entry: Optional[Any] = None
        parent_id: Optional[str] = None
        kind: Optional[str] = None
        associated_person_id: Optional[str] = None

        _name = field_validator("name")(checked_name)

        @field_validator("kind")
        @classmethod
        def _kind(cls, value: Any) -> Any:
            return checked_kind(value, LOCATION_KINDS, "location")

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Search(ApplicationModel.Search):
        name: Optional[StringSearchModel] = None
        description: Optional[StringSearchModel] = None
        kind: Optional[StringSearchModel] = None
        parent_id: Optional[StringSearchModel] = None
        associated_person_id: Optional[StringSearchModel] = None


class LocationManager(AbstractBLLManager, RouterMixin):
    _model = LocationModel


LocationModel.Manager = LocationManager


@hook_bll(LocationManager, timing=HookTiming.BEFORE, priority=10)
def _location_no_cycle(context: HookContext) -> None:
    """A location can't sit under itself or under one of its own descendants."""
    refuse_parent_cycle(context, "location")


# PersonModel is imported so associated_person_id gets its foreign key: the framework names a
# `<entity>_id` column's table from its model, which must be loaded (genealogy is a dependency).
__all__ = ["LocationModel", "PersonModel"]
