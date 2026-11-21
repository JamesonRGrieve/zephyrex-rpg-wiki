# SPDX-License-Identifier: AGPL-3.0-or-later
"""entity_posts models: the same resource, fields and rules as the lite edition's
(client/src/lib/worldRecords.ts).

``/v1/entity_post``: a note on any entity (``target_entity_type`` from contract/wiki.json and its id):
a name, an entry (Plate; the description is its plain text), ``position`` (pinned_top shows first)
and ``ordinal`` (its order within its position). Visibility is acl_rbac's (W9), not a column.
"""

from typing import Any, ClassVar, Optional, Type

from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.wiki_shared.Contract import ENTITY_TYPES, POST_POSITIONS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import checked_kind, checked_name, with_entry_text  # type: ignore[import-not-found]
from zephyrex.logic.AbstractLogicManager import (
    AbstractBLLManager,
    ApplicationModel,
    DescriptionMixinModel,
    ModelMeta,
    NameMixinModel,
    StringSearchModel,
    UpdateMixinModel,
)
from zephyrex.pydantic2.fastapi import RouterMixin

# The framework's registry BaseModel, which it re-exports without declaring it.
from zephyrex.pydantic2.registry import BaseModel  # type: ignore[attr-defined]


def _position(value: Any) -> Any:
    return checked_kind(value, POST_POSITIONS, "post position")


def _target_type(value: Any) -> Any:
    return checked_kind(value, ENTITY_TYPES, "post target")


def _ordinal(value: Any) -> Any:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError("An ordinal is a whole number of zero or more")
    return value


class EntityPostModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["EntityPostManager"]] = None
    target_entity_type: Optional[str] = Field(None, description="contract/wiki.json entity_types")
    target_entity_id: Optional[str] = Field(None, description="The entity's id, in its own table")
    entry: Optional[str] = Field(None, description="The entry: a Plate value as JSON text")
    position: Optional[str] = Field("default", description="contract/wiki.json post_positions")
    ordinal: Optional[int] = Field(0, description="Order within its position (0 first)")
    table_comment: ClassVar[str] = (
        "A post on any entity (target_entity_type + id; polymorphic, no FK, OBJECT_PLAN §7). "
        "pinned_top posts show first. Visibility is acl_rbac's (W9)."
    )

    class Create(BaseModel):
        target_entity_type: str = Field(...)
        target_entity_id: str = Field(...)
        name: str = Field(...)
        description: Optional[str] = None
        entry: Optional[Any] = None
        position: Optional[str] = None
        ordinal: Optional[int] = None

        _name = field_validator("name")(checked_name)
        _type = field_validator("target_entity_type")(_target_type)
        _position = field_validator("position")(_position)
        _ordinal = field_validator("ordinal")(_ordinal)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        entry: Optional[Any] = None
        position: Optional[str] = None
        ordinal: Optional[int] = None

        _name = field_validator("name")(checked_name)
        _position = field_validator("position")(_position)
        _ordinal = field_validator("ordinal")(_ordinal)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Search(ApplicationModel.Search):
        target_entity_type: Optional[StringSearchModel] = None
        target_entity_id: Optional[StringSearchModel] = None
        position: Optional[StringSearchModel] = None


class EntityPostManager(AbstractBLLManager, RouterMixin):
    _model = EntityPostModel


EntityPostModel.Manager = EntityPostManager
