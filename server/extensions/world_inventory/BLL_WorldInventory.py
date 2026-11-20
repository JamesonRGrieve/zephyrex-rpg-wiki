# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_inventory models: the same resources, fields and rules as the lite edition's
(client/src/lib/worldRecords.ts).

- ``/v1/item``: a kind of thing (``kind`` from contract/wiki.json): weight, value, how many stack.
  The campaign and game system are rpg_core's (it injects both).
- ``/v1/item_instance``: one of them in the world: where it is (``location_id``), whose it is
  (``owner_person_id``, "who would notice it missing"), how many (≥1) and its durability.
- ``/v1/entity_inventory``: what an entity carries right now (W8): any person, place, faction or item
  (``target_entity_type`` from the contract, and its id) holding an item instance, so many of it.
  Ownership is de jure, carrying is de facto (OBJECT_PLAN decision 24).

Ported from zephyrex-vtt's rpg_state with the same names, except owner_faction_id, which isn't here
(see __init__.py).
"""

from typing import Any, ClassVar, Optional, Type

from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.genealogy.BLL_Genealogy import PersonModel
from zephyrex.extensions.wiki_shared.Contract import ENTITY_TYPES, ITEM_KINDS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import (  # type: ignore[import-not-found]
    checked_kind,
    checked_name,
    checked_quantity,
    with_entry_text,
)
from zephyrex.extensions.world_spatial.BLL_WorldSpatial import LocationModel  # type: ignore[import-not-found]
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


def _item_kind(value: Any) -> Any:
    return checked_kind(value, ITEM_KINDS, "item")


def _entity_type(value: Any) -> Any:
    if value is None or value in ENTITY_TYPES:
        return value
    raise ValueError(f"An entity type is one of: {', '.join(ENTITY_TYPES)}")


def _not_negative(value: Any) -> Any:
    if value is not None and value < 0:
        raise ValueError("Can't be below zero")
    return value


class ItemModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["ItemManager"]] = None
    kind: Optional[str] = Field(None, description="contract/wiki.json item_kinds")
    entry: Optional[str] = Field(None, description="The entry: a Plate value as JSON text")
    weight: Optional[float] = Field(None, description="Per-unit weight")
    base_value: Optional[float] = Field(None, description="Default value per unit")
    stack_size: Optional[int] = Field(1, description="Most units per stack (1 = doesn't stack)")
    table_comment: ClassVar[str] = "A kind of thing (the catalogue). ItemInstance is one of them in the world."

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        entry: Optional[Any] = None
        kind: Optional[str] = None
        weight: Optional[float] = None
        base_value: Optional[float] = None
        stack_size: Optional[int] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_item_kind)
        _amounts = field_validator("weight", "base_value")(_not_negative)
        _stack = field_validator("stack_size")(checked_quantity)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        entry: Optional[Any] = None
        kind: Optional[str] = None
        weight: Optional[float] = None
        base_value: Optional[float] = None
        stack_size: Optional[int] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_item_kind)
        _amounts = field_validator("weight", "base_value")(_not_negative)
        _stack = field_validator("stack_size")(checked_quantity)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Search(ApplicationModel.Search):
        name: Optional[StringSearchModel] = None
        description: Optional[StringSearchModel] = None
        kind: Optional[StringSearchModel] = None


class ItemManager(AbstractBLLManager, RouterMixin):
    _model = ItemModel


ItemModel.Manager = ItemManager


class ItemInstanceModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    ItemModel.Reference.Optional,
    LocationModel.Reference.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["ItemInstanceManager"]] = None
    owner_person_id: Optional[str] = Field(None, description="Whose it is: who would notice it missing")
    quantity: Optional[int] = Field(1, description="How many (≥1)")
    durability: Optional[float] = Field(None, description="System-defined durability")
    table_comment: ClassVar[str] = (
        "One item in the world: location_id = where it is; owner_person_id = whose it is (de jure). "
        "Who carries it now is EntityInventory (de facto)."
    )

    class Create(BaseModel, ItemModel.Reference.ID.Optional, LocationModel.Reference.ID.Optional):
        owner_person_id: Optional[str] = None
        quantity: Optional[int] = None
        durability: Optional[float] = None

        _quantity = field_validator("quantity")(checked_quantity)

    class Update(BaseModel):
        location_id: Optional[str] = None
        owner_person_id: Optional[str] = None
        quantity: Optional[int] = None
        durability: Optional[float] = None

        _quantity = field_validator("quantity")(checked_quantity)

    class Search(ApplicationModel.Search, ItemModel.Reference.ID.Search, LocationModel.Reference.ID.Search):
        owner_person_id: Optional[StringSearchModel] = None


class ItemInstanceManager(AbstractBLLManager, RouterMixin):
    _model = ItemInstanceModel


ItemInstanceModel.Manager = ItemInstanceManager


class EntityInventoryModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    ItemInstanceModel.Reference.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["EntityInventoryManager"]] = None
    target_entity_type: Optional[str] = Field(None, description="contract/wiki.json entity_types")
    target_entity_id: Optional[str] = Field(None, description="The carrier's id, in its own table")
    quantity: Optional[int] = Field(1, description="How many it carries (≥1)")
    table_comment: ClassVar[str] = (
        "What an entity carries now (W8): any person, place, faction or item (target_entity_type + id) "
        "holding an item instance. Polymorphic, so no FK on the target (OBJECT_PLAN §7)."
    )

    class Create(BaseModel, ItemInstanceModel.Reference.ID.Optional):
        target_entity_type: str = Field(...)
        target_entity_id: str = Field(...)
        quantity: Optional[int] = None

        _type = field_validator("target_entity_type")(_entity_type)
        _quantity = field_validator("quantity")(checked_quantity)

    class Update(BaseModel):
        quantity: Optional[int] = None

        _quantity = field_validator("quantity")(checked_quantity)

    class Search(ApplicationModel.Search, ItemInstanceModel.Reference.ID.Search):
        target_entity_type: Optional[StringSearchModel] = None
        target_entity_id: Optional[StringSearchModel] = None


class EntityInventoryManager(AbstractBLLManager, RouterMixin):
    _model = EntityInventoryModel


EntityInventoryModel.Manager = EntityInventoryManager

# PersonModel is imported for owner_person_id's foreign key: the framework names a `<entity>_id`
# column's table from its model, which must be loaded (genealogy is a dependency).
__all__ = ["EntityInventoryModel", "ItemInstanceModel", "ItemModel", "PersonModel"]
