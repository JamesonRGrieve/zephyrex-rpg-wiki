# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core models: the same resources, fields and rules as the lite edition's
(client/src/lib/campaignRecords.ts, personRecords.ts).

- ``/v1/campaign``: a world. Its owner is ``user_id``.
- ``/v1/person`` (genealogy's) gains ``kind`` (contract/wiki.json person_kinds), ``campaign_id``,
  ``user_id`` (the player; none for an NPC), ``location_id`` (where they are) and ``entry`` (a Plate
  value, its plain text kept as the description).
- ``/v1/location`` (world_spatial's) and ``/v1/faction`` (world_social's) gain ``campaign_id``.
- ``/v1/item`` (world_inventory's) gains ``campaign_id``.

Rule systems (game_systems, and game_system_id on campaigns and items) are zephyrex-vtt's
rpg_systems (operator, 2026-11-20): the wiki depends on no other suite product.

Each ``*_id`` names its model, so the framework gives it a real foreign key.
"""

from typing import Any, ClassVar, Optional, Type

from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.genealogy.BLL_Genealogy import PersonModel
from zephyrex.extensions.wiki_shared.Contract import PERSON_KINDS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import (  # type: ignore[import-not-found]
    checked_kind,
    checked_name,
    with_entry_text,
)
from zephyrex.extensions.world_inventory.BLL_WorldInventory import ItemModel  # type: ignore[import-not-found]
from zephyrex.extensions.world_social.BLL_WorldSocial import FactionModel  # type: ignore[import-not-found]
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
from zephyrex.logic.BLL_Auth import UserModel
from zephyrex.pydantic2.fastapi import RouterMixin

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
