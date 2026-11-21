# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_social models: the same resource, fields and rules as the lite edition's
(client/src/lib/worldRecords.ts).

``/v1/faction``: an organisation or a family (``kind`` from contract/wiki.json), under its parent
(squads within platoons, houses within a dynasty). Its entry is a Plate value; its description is
the entry's plain text. Ported from zephyrex-vtt's rpg_state.FactionModel with the same names
(OBJECT_PLAN §6); the campaign link is rpg_core's. A parent change that would close a cycle is
refused (422).

Relations (W5) are genealogy's ``/v1/relationship``, widened here as OBJECT_PLAN §3 has it: either
side is a person or an organisation (``faction_id``, ``target_faction_id``; exactly one per side,
422 otherwise), with a ``colour``; attitude is genealogy's ``intensity`` (-1 to +1). A relation can
name its ``mirror_relationship_id``, the same tie read the other way (endpoints swapped): the two
are then kept in step, and deleting one deletes the other. Moved from vtt's rpg_state.
"""

from typing import Any, ClassVar, Optional, Type

from fastapi import HTTPException

from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.genealogy.BLL_Genealogy import RelationshipManager, RelationshipModel
from zephyrex.extensions.wiki_shared.Contract import FACTION_KINDS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import (  # type: ignore[import-not-found]
    checked_colour,
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
from zephyrex.pydantic2.sqlalchemy import extension_model

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


# ---------------------------------------------------------------------------
# Relations (W5): organisations as endpoints, colour, mirror
# ---------------------------------------------------------------------------


@extension_model(RelationshipModel)
class WS_RelationshipModel(BaseModel):
    """Organisation endpoints, a colour and a mirror on genealogy's relationships."""

    faction_id: Optional[str] = Field(None, description="FK → factions.id; the subject, when an organisation (XOR person_id)")
    target_faction_id: Optional[str] = Field(None, description="FK → factions.id; the object, when an organisation (XOR target_person_id)")
    colour: Optional[str] = Field(None, description="#rrggbb")
    mirror_relationship_id: Optional[str] = Field(None, description="The same tie read the other way; kept in step")

    class Create(BaseModel):
        faction_id: Optional[str] = None
        target_faction_id: Optional[str] = None
        colour: Optional[str] = None
        mirror_relationship_id: Optional[str] = None

        _colour = field_validator("colour")(checked_colour)

    class Update(BaseModel):
        colour: Optional[str] = None

        _colour = field_validator("colour")(checked_colour)

    class Search(BaseModel):
        faction_id: Optional[StringSearchModel] = None
        target_faction_id: Optional[StringSearchModel] = None
        mirror_relationship_id: Optional[StringSearchModel] = None


# What a mirror shares with its relation; endpoints are swapped, not shared.
MIRRORED = ("kind", "discriminator", "intensity", "qualifier", "valid_from", "valid_to", "notes", "colour")


@hook_bll(RelationshipManager, timing=HookTiming.BEFORE, priority=10)
def _one_endpoint_a_side(context: HookContext) -> None:
    """Each side is a person or an organisation, never both or neither; a mirror swaps the ends."""
    if context.method_name != "create":
        return
    subject = [context.kwarg("person_id"), context.kwarg("faction_id")]
    target = [context.kwarg("target_person_id"), context.kwarg("target_faction_id")]
    if sum(value is not None for value in subject) != 1 or sum(value is not None for value in target) != 1:
        raise HTTPException(status_code=422, detail="Each side of a relation is one person or one organisation")
    if context.kwarg("faction_id") is not None and context.kwarg("faction_id") == context.kwarg("target_faction_id"):
        raise HTTPException(status_code=422, detail="A relation needs two different organisations")
    mirror_id = context.kwarg("mirror_relationship_id")
    if mirror_id:
        try:
            other = context.manager.get(id=mirror_id)
        except HTTPException as error:
            raise HTTPException(status_code=422, detail="That mirror relation is not one of yours") from error
        swapped = (
            other.person_id == context.kwarg("target_person_id")
            and other.target_person_id == context.kwarg("person_id")
            and getattr(other, "faction_id", None) == context.kwarg("target_faction_id")
            and getattr(other, "target_faction_id", None) == context.kwarg("faction_id")
        )
        if not swapped:
            raise HTTPException(status_code=422, detail="A mirror has the same two ends, the other way round")
        if getattr(other, "mirror_relationship_id", None):
            raise HTTPException(status_code=422, detail="That relation already has a mirror")


@hook_bll(RelationshipManager, timing=HookTiming.AFTER, priority=10)
def _mirror_in_step(context: HookContext) -> None:
    """A new mirror links back; a change reaches the mirror; a deleted relation takes its mirror."""
    manager = context.manager
    if context.method_name == "create":
        created = context.result
        mirror_id = getattr(created, "mirror_relationship_id", None)
        if mirror_id:
            manager.update_trusted(mirror_id, mirror_relationship_id=str(created.id))
        return
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if not record_id:
        return
    if context.method_name == "update":
        current = manager.get(id=record_id)
        mirror_id = getattr(current, "mirror_relationship_id", None)
        if not mirror_id:
            return
        mirror = manager.get(id=mirror_id)
        changed = {field: context.kwarg(field) for field in MIRRORED if field in context.kwargs and getattr(mirror, field, None) != context.kwarg(field)}
        if changed:
            manager.update(mirror_id, **changed)
    elif context.method_name == "delete":
        rows = manager.list(mirror_relationship_id=record_id) or []
        for row in rows:
            manager.delete(id=row.id)
