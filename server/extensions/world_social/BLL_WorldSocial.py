# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_social models: the same resource, fields and rules as the lite edition's
(client/src/lib/worldRecords.ts).

``/v1/faction``: an organisation or a family (``kind`` from contract/wiki.json), under its parent
(squads within platoons, houses within a dynasty). Its entry is a Plate value; its description is
the entry's plain text. Ported from zephyrex-vtt's rpg_state.FactionModel with the same names
(OBJECT_PLAN §6); the campaign link is rpg_core's. A parent change that would close a cycle is
refused (422).
"""

from typing import Any, ClassVar, Optional, Type

from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.wiki_shared.Contract import FACTION_KINDS  # type: ignore[import-not-found]
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


def _faction_kind(value: Any) -> Any:
    return checked_kind(value, FACTION_KINDS, "faction")


class FactionModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    ParentMixinModel.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["FactionManager"]] = None
    kind: Optional[str] = Field(None, description="contract/wiki.json faction_kinds")
    entry: Optional[str] = Field(None, description="The entry: a Plate value as JSON text")
    table_comment: ClassVar[str] = (
        "An organisation or family, under its parent (parent_id). entry is a Plate value; description "
        "is its plain-text copy, for search."
    )

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        entry: Optional[Any] = None
        parent_id: Optional[str] = None
        kind: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_faction_kind)

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
        _kind = field_validator("kind")(_faction_kind)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Search(ApplicationModel.Search):
        name: Optional[StringSearchModel] = None
        description: Optional[StringSearchModel] = None
        kind: Optional[StringSearchModel] = None
        parent_id: Optional[StringSearchModel] = None


class FactionManager(AbstractBLLManager, RouterMixin):
    _model = FactionModel


FactionModel.Manager = FactionManager


@hook_bll(FactionManager, timing=HookTiming.BEFORE, priority=10)
def _faction_no_cycle(context: HookContext) -> None:
    """A faction can't sit under itself or under one of its own descendants."""
    refuse_parent_cycle(context, "faction")
