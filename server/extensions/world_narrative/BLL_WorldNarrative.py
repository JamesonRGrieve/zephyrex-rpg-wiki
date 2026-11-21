# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_narrative models: the same resource, fields and rules as the lite edition's
(client/src/lib/worldRecords.ts).

``/v1/journal``: a session report, in-world diary, piece of lore, handout, note, manuscript, prose or
chapter (``kind`` from contract/wiki.json), with its entry (a Plate value; the description is its
plain text), where it's set (``location_id``), who wrote it (``author_person_id``), and for a session
report its ``session_number`` and when it happened (``occurred_at``). The campaign link is rpg_core's.
"""

from datetime import datetime
from typing import Any, ClassVar, Optional, Type

from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.genealogy.BLL_Genealogy import PersonModel
from zephyrex.extensions.wiki_shared.Contract import JOURNAL_KINDS  # type: ignore[import-not-found]
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
    DateSearchModel,
    DescriptionMixinModel,
    ModelMeta,
    NameMixinModel,
    NumericalSearchModel,
    StringSearchModel,
    UpdateMixinModel,
)
from zephyrex.pydantic2.fastapi import RouterMixin

# The framework's registry BaseModel, which it re-exports without declaring it.
from zephyrex.pydantic2.registry import BaseModel  # type: ignore[attr-defined]


def _journal_kind(value: Any) -> Any:
    return checked_kind(value, JOURNAL_KINDS, "journal")


class JournalModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    LocationModel.Reference.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["JournalManager"]] = None
    kind: Optional[str] = Field(None, description="contract/wiki.json journal_kinds")
    entry: Optional[str] = Field(None, description="The entry: a Plate value as JSON text")
    author_person_id: Optional[str] = Field(None, description="FK → persons.id; who wrote it")
    session_number: Optional[int] = Field(None, description="For a session report: which session (≥1)")
    occurred_at: Optional[datetime] = Field(None, description="When what it records happened")
    table_comment: ClassVar[str] = (
        "A journal: session report, diary, lore, handout, note, manuscript, prose or chapter. entry is a "
        "Plate value; description is its plain-text copy, for search."
    )

    class Create(BaseModel, LocationModel.Reference.ID.Optional):
        name: str = Field(...)
        description: Optional[str] = None
        entry: Optional[Any] = None
        kind: Optional[str] = None
        author_person_id: Optional[str] = None
        session_number: Optional[int] = None
        occurred_at: Optional[datetime] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_journal_kind)
        _session = field_validator("session_number")(checked_quantity)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        entry: Optional[Any] = None
        kind: Optional[str] = None
        location_id: Optional[str] = None
        author_person_id: Optional[str] = None
        session_number: Optional[int] = None
        occurred_at: Optional[datetime] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_journal_kind)
        _session = field_validator("session_number")(checked_quantity)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Search(ApplicationModel.Search, LocationModel.Reference.ID.Search):
        name: Optional[StringSearchModel] = None
        description: Optional[StringSearchModel] = None
        kind: Optional[StringSearchModel] = None
        author_person_id: Optional[StringSearchModel] = None
        session_number: Optional[NumericalSearchModel] = None
        occurred_at: Optional[DateSearchModel] = None


class JournalManager(AbstractBLLManager, RouterMixin):
    _model = JournalModel


JournalModel.Manager = JournalManager

# PersonModel is imported so author_person_id gets its foreign key (genealogy is a dependency).
__all__ = ["JournalModel", "PersonModel"]
