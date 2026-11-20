# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_spatial models: a location tree, the same resource, fields and rules as the lite
edition's (client/src/lib/locationRecords.ts).

``/v1/location``: a place at any scale (``kind`` from contract/wiki.json), under its parent. Its
entry is a Plate value; its description is the entry's plain-text copy, for search (Entry.py).
Ported from zephyrex-vtt's rpg_state.LocationModel with the same table and field names
(OBJECT_PLAN §6). The campaign link is rpg_core's (it injects ``campaign_id``), so this tier
stays campaign-free. A parent change that would close a cycle is refused.
"""

from typing import Any, ClassVar, Optional, Type

from fastapi import HTTPException
from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.world_spatial.Contract import LIMITS, LOCATION_KINDS  # type: ignore[import-not-found]
from zephyrex.extensions.world_spatial.Entry import parse as parse_entry  # type: ignore[import-not-found]
from zephyrex.lib.CycleGuard import CycleGuardError, would_create_tree_cycle
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

MAX_NAME: int = LIMITS["name_characters"]


def checked_name(value: Any) -> Any:
    """A name, trimmed: required, and at most the contract's length."""
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        raise ValueError("A name is required")
    if len(stripped) > MAX_NAME:
        raise ValueError(f"A name has at most {MAX_NAME} characters")
    return stripped


def checked_kind(value: Any, kinds: tuple[str, ...], what: str) -> Any:
    """A kind from the contract's list for ``what``, or None."""
    if value is None or value in kinds:
        return value
    raise ValueError(f"A {what}'s kind is one of: {', '.join(kinds)}")


def with_entry_text(payload: Any) -> Any:
    """Store the entry as compact JSON text and its plain-text copy as the description."""
    entry = getattr(payload, "entry", None)
    if entry is not None:
        stored, text = parse_entry(entry)
        payload.entry = stored
        payload.description = text
    return payload


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
    table_comment: ClassVar[str] = (
        "A place at any scale, under its parent (parent_id). entry is a Plate value; description "
        "is its plain-text copy, for search."
    )

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        entry: Optional[Any] = None
        parent_id: Optional[str] = None
        kind: Optional[str] = None

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


class LocationManager(AbstractBLLManager, RouterMixin):
    _model = LocationModel


LocationModel.Manager = LocationManager


def _parent_of(manager: AbstractBLLManager) -> Any:
    def _get(location_id: str) -> Optional[str]:
        try:
            row = manager.get(id=location_id)
        except Exception:
            return None
        return getattr(row, "parent_id", None) if row else None

    return _get


@hook_bll(LocationManager, timing=HookTiming.BEFORE, priority=10)
def _location_no_cycle(context: HookContext) -> None:
    """A location can't sit under itself or under one of its own descendants."""
    if context.method_name != "update":
        return
    candidate = context.kwarg("parent_id", default=None)
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if not candidate or not record_id:
        return
    try:
        cycle = would_create_tree_cycle(record_id, candidate, _parent_of(context.manager))
    except CycleGuardError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if cycle:
        # 422, as the lite edition answers: a request the server understood but won't apply.
        raise HTTPException(status_code=422, detail="A location can't sit under itself or its own descendants")
