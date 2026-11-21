# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_properties models (W4): the same resources, fields and rules as the lite edition's
(client/src/lib/worldRecords.ts).

- ``/v1/property_kit``: a property kit: a name, a description, and ``properties``, the kit's keys
  as JSON (``[{key, value_type, default, is_private, ordinal}]``, wiki_shared/Properties.py).
- ``POST /v1/property_kit/{id}/apply``: adds each of the kit's keys that a record doesn't have yet
  to that record's own key/values, through the framework's record_metadata and so under its rules
  (anyone who can view the kit; EDIT on the record; a record's 200 keys). Keys the record already
  has are kept as they are and named as skipped.

A record's properties themselves are the framework's ``/v1/record_metadata``: the wiki keeps no
table of values. The campaign and setting on a kit are rpg_core's.
"""

import json
from typing import Any, ClassVar, Optional, Type

from fastapi import HTTPException
from pydantic import BaseModel as RouteModel
from pydantic import Field, field_validator
from zephyrex.extensions.wiki_shared.Properties import KitError, checked_kit  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import checked_name  # type: ignore[import-not-found]
from zephyrex.lib.CustomRoute import ExposeIn, custom_route
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


def _kit_text(value: Any) -> Any:
    """A kit's properties arrive as JSON (a string or the list) and are kept as JSON text."""
    if value is None:
        return None
    try:
        properties = json.loads(value) if isinstance(value, str) else value
        return json.dumps(checked_kit(properties), separators=(",", ":"))
    except (KitError, json.JSONDecodeError) as error:
        raise ValueError(str(error)) from error


def properties_of(kit: Any) -> list[dict[str, Any]]:
    """A kit's properties, as stored (already checked)."""
    text = getattr(kit, "properties", None)
    loaded: list[dict[str, Any]] = json.loads(text) if text else []
    return loaded


class PropertyKitModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["PropertyKitManager"]] = None
    properties: Optional[str] = Field(None, description="The kit's keys as JSON: [{key, value_type, default, is_private, ordinal}]")
    table_comment: ClassVar[str] = "A property kit (W4): keys with types and defaults, applied to any record's properties."

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        properties: Optional[Any] = None

        _name = field_validator("name")(checked_name)
        _properties = field_validator("properties")(_kit_text)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        properties: Optional[Any] = None

        _name = field_validator("name")(checked_name)
        _properties = field_validator("properties")(_kit_text)

    class Search(ApplicationModel.Search):
        name: Optional[StringSearchModel] = None


class KitApplication(RouteModel):
    target_entity_type: str = Field(..., description="The record's type: its model's snake-case name")
    target_entity_id: str = Field(..., description="The record's id")


class KitApplicationEnvelope(RouteModel):
    application: KitApplication


class KitApplied(RouteModel):
    added: list[str] = Field(..., description="The keys added to the record, in the kit's order")
    skipped: list[str] = Field(..., description="The kit's keys the record already had, kept as they were")


class PropertyKitManager(AbstractBLLManager, RouterMixin):
    _model = PropertyKitModel

    @custom_route(
        method="POST",
        path="/{id}/apply",
        input_model=KitApplicationEnvelope,
        output_model=KitApplied,
        authentication_type="jwt",
        openapi_tags=("Property kits",),
        summary="Add the kit's keys a record doesn't have yet to its properties (EDIT on the record)",
        expose_in=(ExposeIn.REST,),
    )
    def apply_route(self, id: str, application: KitApplication) -> KitApplied:
        from zephyrex.extensions.metadata.BLL_Metadata import RecordMetadataManager, RecordMetadataWrite

        target = KitApplication.model_validate(application)
        kit = self.get(id=id)
        records = RecordMetadataManager(requester_id=str(self.requester.id), model_registry=self.model_registry)
        # Reading the record's rows first is the VIEW check (404); each add is the EDIT check.
        held = {row.key for row in records.of_route(target.target_entity_type, target.target_entity_id).metadata}
        wanted = sorted(properties_of(kit), key=lambda one: one["ordinal"])
        if not wanted:
            raise HTTPException(status_code=422, detail="The kit has no properties to apply")
        added: list[str] = []
        skipped: list[str] = []
        for one in wanted:
            if one["key"] in held:
                skipped.append(one["key"])
                continue
            records.add_route(
                RecordMetadataWrite(
                    target_entity_type=target.target_entity_type,
                    target_entity_id=target.target_entity_id,
                    key=one["key"],
                    value=one["default"],
                    value_type=one["value_type"],
                    ordinal=one["ordinal"],
                    is_private=one["is_private"],
                )
            )
            added.append(one["key"])
        return KitApplied(added=added, skipped=skipped)


PropertyKitModel.Manager = PropertyKitManager
