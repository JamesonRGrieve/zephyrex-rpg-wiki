# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_narrative models: the same resource, fields and rules as the lite edition's
(client/src/lib/worldRecords.ts).

``/v1/journal``: a session report, in-world diary, piece of lore, handout, note, manuscript, prose or
chapter (``kind`` from contract/wiki.json), with its entry (a Plate value; the description is its
plain text), where it's set (``location_id``), who wrote it (``author_person_id``), and for a session
report its ``session_number`` and when it happened (``occurred_at``). The campaign link is rpg_core's.

``/v1/hook``: a plot hook (quest, objective, thread, mystery, rumour…; ``kind`` from the contract),
who gave it (``giver_person_id``, ``giver_faction_id``) and its entry. Hooks form a DAG through
``/v1/hook_dependency`` (parent = the prerequisite, child = what it leads to; a cycle is refused),
and each person's or faction's progress on one is a ``/v1/person_hook`` or ``/v1/faction_hook``
(status free-form, at most 40 characters; one per actor and hook). Deleting a hook removes its
dependencies and progress rows. Moved here from vtt's rpg_state (OBJECT_PLAN §6).
"""

import json
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Callable, ClassVar, Iterable, Optional, Type

from fastapi import HTTPException
from pydantic import Field, field_validator, model_validator
from zephyrex.extensions.genealogy.BLL_Genealogy import PersonModel, RelationshipModel
from zephyrex.extensions.wiki_shared.Contract import DISPOSITION_TARGETS, HOOK_KINDS, JOURNAL_KINDS, LIMITS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Dispositions import checked_attitude  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import (  # type: ignore[import-not-found]
    checked_kind,
    checked_name,
    checked_quantity,
    with_entry_text,
)
from zephyrex.extensions.wiki_shared.Requirements import RequirementError, leaves  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Requirements import checked as checked_requirement  # type: ignore[import-not-found]
from zephyrex.extensions.world_social.BLL_WorldSocial import FactionModel  # type: ignore[import-not-found]
from zephyrex.extensions.world_spatial.BLL_WorldSpatial import LocationModel  # type: ignore[import-not-found]
from zephyrex.lib.CycleGuard import CycleGuardError, would_create_dag_cycle
from zephyrex.logic.AbstractLogicManager import (
    AbstractBLLManager,
    ApplicationModel,
    DateSearchModel,
    DescriptionMixinModel,
    HookContext,
    HookTiming,
    ModelMeta,
    NameMixinModel,
    NumericalSearchModel,
    StringSearchModel,
    UpdateMixinModel,
    hook_bll,
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


# ---------------------------------------------------------------------------
# Hooks: the plot-hook DAG and who is on each hook
# ---------------------------------------------------------------------------


def _hook_kind(value: Any) -> Any:
    return checked_kind(value, HOOK_KINDS, "hook")


def _requirement_text(value: Any) -> Any:
    """A requirement arrives as JSON (a string or the structure) and is kept as JSON text."""
    if value is None or value == "":
        return None
    try:
        node = json.loads(value) if isinstance(value, str) and value[:1] in "[{\"" else value
        checked_requirement(node)
    except (RequirementError, json.JSONDecodeError) as error:
        raise ValueError(str(error)) from error
    if len(leaves(node)) > LIMITS["requirement_leaves"]:
        raise ValueError(f"A requirement names at most {LIMITS['requirement_leaves']} hooks")
    return json.dumps(node, separators=(",", ":"))


def _status(value: Any) -> Any:
    if value is not None and len(value) > LIMITS["hook_status_characters"]:
        raise ValueError(f"A status is at most {LIMITS['hook_status_characters']} characters")
    return value


def _progress(value: Any) -> Any:
    if value is not None and value < 0:
        raise ValueError("Progress is zero or more")
    return value


class HookModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    NameMixinModel.Optional,
    DescriptionMixinModel.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["HookManager"]] = None
    kind: Optional[str] = Field(None, description="contract/wiki.json hook_kinds")
    entry: Optional[str] = Field(None, description="The entry: a Plate value as JSON text")
    giver_person_id: Optional[str] = Field(None, description="FK → persons.id; who gave the hook")
    giver_faction_id: Optional[str] = Field(None, description="FK → factions.id; the organisation that gave it")
    requires: Optional[str] = Field(None, description="Requirement as JSON: a hook id, all, any or char (W57)")
    excuse: Optional[str] = Field(None, description="GM-facing: why it's blocked")
    resolved_at: Optional[datetime] = Field(None, description="When it happened; none = not yet")
    resolved_journal_id: Optional[str] = Field(None, description="FK → journals.id; the session report it happened in")
    table_comment: ClassVar[str] = (
        "A plot hook: quest, objective, thread, mystery, rumour, obligation, foreshadowing, hint or "
        "background. Prerequisites are hook_dependencies; progress is person_hooks and faction_hooks."
    )

    class Create(BaseModel):
        name: str = Field(...)
        description: Optional[str] = None
        entry: Optional[Any] = None
        kind: Optional[str] = None
        giver_person_id: Optional[str] = None
        giver_faction_id: Optional[str] = None
        requires: Optional[Any] = None
        excuse: Optional[str] = None
        resolved_at: Optional[datetime] = None
        resolved_journal_id: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_hook_kind)
        _requires = field_validator("requires")(_requirement_text)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Update(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        entry: Optional[Any] = None
        kind: Optional[str] = None
        giver_person_id: Optional[str] = None
        giver_faction_id: Optional[str] = None
        requires: Optional[Any] = None
        excuse: Optional[str] = None
        resolved_at: Optional[datetime] = None
        resolved_journal_id: Optional[str] = None

        _name = field_validator("name")(checked_name)
        _kind = field_validator("kind")(_hook_kind)
        _requires = field_validator("requires")(_requirement_text)

        @model_validator(mode="after")
        def _entry(self) -> Any:
            return with_entry_text(self)

    class Search(ApplicationModel.Search):
        name: Optional[StringSearchModel] = None
        description: Optional[StringSearchModel] = None
        kind: Optional[StringSearchModel] = None
        giver_person_id: Optional[StringSearchModel] = None
        giver_faction_id: Optional[StringSearchModel] = None
        resolved_at: Optional[DateSearchModel] = None


class HookManager(AbstractBLLManager, RouterMixin):
    _model = HookModel


HookModel.Manager = HookManager


_FROM_REQUIREMENT: ContextVar[bool] = ContextVar("_FROM_REQUIREMENT", default=False)


class HookDependencyModel(ApplicationModel.Optional, UpdateMixinModel.Optional, metaclass=ModelMeta):
    Manager: ClassVar[Type["HookDependencyManager"]] = None
    # Both ends are hooks: named columns, since HookModel.Reference would make one hook_id for both.
    parent_hook_id: Optional[str] = Field(None, description="FK → hooks.id; the prerequisite")
    child_hook_id: Optional[str] = Field(None, description="FK → hooks.id; what it leads to")
    reason: Optional[str] = Field(None, description="Why the child waits on the parent")
    table_comment: ClassVar[str] = "An edge of the hook DAG: the child hook waits on the parent. No cycles."

    class Create(BaseModel):
        parent_hook_id: str = Field(...)
        child_hook_id: str = Field(...)
        reason: Optional[str] = None

    class Update(BaseModel):
        reason: Optional[str] = None

    class Search(ApplicationModel.Search):
        parent_hook_id: Optional[StringSearchModel] = None
        child_hook_id: Optional[StringSearchModel] = None


class HookDependencyManager(AbstractBLLManager, RouterMixin):
    _model = HookDependencyModel


HookDependencyModel.Manager = HookDependencyManager


class _Progress(BaseModel):
    status: Optional[str] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: Optional[float] = None

    _status = field_validator("status")(_status)
    _progress = field_validator("progress")(_progress)


class PersonHookModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    PersonModel.Reference.Optional,
    HookModel.Reference.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["PersonHookManager"]] = None
    status: Optional[str] = Field(None, description="Free-form: available, active, completed, failed, resolved…")
    accepted_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    progress: Optional[float] = Field(None, description="For incremental hooks (3 of 5 wolves); none for atomic ones")
    table_comment: ClassVar[str] = "A person's progress on a hook; one per person and hook."

    class Create(_Progress, PersonModel.Reference.ID, HookModel.Reference.ID):
        pass

    class Update(_Progress):
        pass

    class Search(ApplicationModel.Search, PersonModel.Reference.ID.Search, HookModel.Reference.ID.Search):
        status: Optional[StringSearchModel] = None
        progress: Optional[NumericalSearchModel] = None


class PersonHookManager(AbstractBLLManager, RouterMixin):
    _model = PersonHookModel


PersonHookModel.Manager = PersonHookManager


class FactionHookModel(
    ApplicationModel.Optional,
    UpdateMixinModel.Optional,
    FactionModel.Reference.Optional,
    HookModel.Reference.Optional,
    metaclass=ModelMeta,
):
    Manager: ClassVar[Type["FactionHookManager"]] = None
    status: Optional[str] = Field(None, description="Free-form, as a person's")
    accepted_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    progress: Optional[float] = Field(None)
    table_comment: ClassVar[str] = "An organisation's progress on a hook; one per organisation and hook."

    class Create(_Progress, FactionModel.Reference.ID, HookModel.Reference.ID):
        pass

    class Update(_Progress):
        pass

    class Search(ApplicationModel.Search, FactionModel.Reference.ID.Search, HookModel.Reference.ID.Search):
        status: Optional[StringSearchModel] = None
        progress: Optional[NumericalSearchModel] = None


class FactionHookManager(AbstractBLLManager, RouterMixin):
    _model = FactionHookModel


FactionHookModel.Manager = FactionHookManager


def _parents_of(manager: AbstractBLLManager) -> Callable[[str], Iterable[str]]:
    def parents(child_hook_id: str) -> list[str]:
        return [str(edge.parent_hook_id) for edge in manager.list(child_hook_id=child_hook_id) or [] if edge.parent_hook_id]

    return parents


@hook_bll(HookDependencyManager, timing=HookTiming.BEFORE, priority=10)
def _dependency_no_cycle(context: HookContext) -> None:
    """A hook can't wait on itself, on what waits on it, or on the same parent twice."""
    if context.method_name != "create":
        return
    parent = context.kwarg("parent_hook_id", default=None)
    child = context.kwarg("child_hook_id", default=None)
    if not parent or not child:
        return
    try:
        cycle = would_create_dag_cycle(str(parent), str(child), _parents_of(context.manager))
    except CycleGuardError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if cycle:
        raise HTTPException(status_code=422, detail="A hook can't wait on itself or on a hook that waits on it")
    if context.manager.list(parent_hook_id=parent, child_hook_id=child):
        raise HTTPException(status_code=422, detail="That dependency is already there")


def _one_per(actor: str) -> Callable[[HookContext], None]:
    def check(context: HookContext) -> None:
        if context.method_name != "create":
            return
        actor_id = context.kwarg(actor, default=None)
        hook_id = context.kwarg("hook_id", default=None)
        if actor_id and hook_id and context.manager.list(**{actor: actor_id, "hook_id": hook_id}):
            raise HTTPException(status_code=422, detail="That one is already on this hook: update its progress instead")

    return check


hook_bll(PersonHookManager, timing=HookTiming.BEFORE, priority=10)(_one_per("person_id"))
hook_bll(FactionHookManager, timing=HookTiming.BEFORE, priority=10)(_one_per("faction_id"))


@hook_bll(HookManager, timing=HookTiming.AFTER, priority=10)
def _hook_takes_its_links(context: HookContext) -> None:
    """Deleting a hook removes its dependencies (either end) and everyone's progress on it."""
    if context.method_name != "delete":
        return
    hook_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    if not hook_id:
        return
    for manager_class, field in (
        (HookDependencyManager, "parent_hook_id"),
        (HookDependencyManager, "child_hook_id"),
        (PersonHookManager, "hook_id"),
        (FactionHookManager, "hook_id"),
        (DispositionManager, "trigger_hook_id"),
        (RelationInfluenceManager, "hook_id"),
    ):
        manager = manager_class(requester_id=context.manager.requester.id, model_registry=context.manager.model_registry)
        for row in manager.list(**{field: hook_id}) or []:
            manager.delete(id=row.id)



def _requirement_node(value: Any) -> Any:
    """A requirement as hooks see it: BEFORE a create, the raw request value (a bare hook id, JSON
    text or the structure); after validation, the stored JSON text. Either way, the structure."""
    text = _requirement_text(value)
    return json.loads(text) if text else None


def requirement_of(record: Any) -> Any:
    """A hook's requirement as a structure, or none."""
    return _requirement_node(getattr(record, "requires", None))


@hook_bll(HookManager, timing=HookTiming.BEFORE, priority=15)
def _requirement_closes_no_cycle(context: HookContext) -> None:
    """Every hook a requirement names is a prerequisite: none may already wait on this hook."""
    if context.method_name not in ("create", "update"):
        return
    try:
        node = _requirement_node(context.kwarg("requires", default=None))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if node is None:
        return
    record_id = context.kwarg("id", default=None) or context.arg(0, default=None)
    dependencies = HookDependencyManager(requester_id=context.manager.requester.id, model_registry=context.manager.model_registry)
    for leaf in leaves(node):
        try:
            context.manager.get(id=leaf)
        except HTTPException as error:
            raise HTTPException(status_code=422, detail="A requirement names a hook that isn't one of yours") from error
        if record_id and would_create_dag_cycle(leaf, str(record_id), _parents_of(dependencies)):
            raise HTTPException(status_code=422, detail="A hook can't wait on itself or on a hook that waits on it")


@hook_bll(HookManager, timing=HookTiming.AFTER, priority=15)
def _requirement_is_the_edges(context: HookContext) -> None:
    """A hook with a requirement waits on exactly the hooks it names: its incoming edges follow."""
    if context.method_name not in ("create", "update") or "requires" not in context.kwargs:
        return
    hook = context.result
    hook_id = str(hook.id)
    wanted = leaves(requirement_of(hook)) if getattr(hook, "requires", None) else []
    dependencies = HookDependencyManager(requester_id=context.manager.requester.id, model_registry=context.manager.model_registry)
    have = {str(edge.parent_hook_id): edge for edge in dependencies.list(child_hook_id=hook_id) or []}
    for parent, edge in have.items():
        if parent not in wanted:
            dependencies.delete(id=edge.id)
    for parent in wanted:
        if parent not in have:
            token = _FROM_REQUIREMENT.set(True)
            try:
                dependencies.create(parent_hook_id=parent, child_hook_id=hook_id, reason="requirement")
            finally:
                _FROM_REQUIREMENT.reset(token)


@hook_bll(HookDependencyManager, timing=HookTiming.BEFORE, priority=5)
def _requirement_owns_its_edges(context: HookContext) -> None:
    """A hook whose requirement is an expression gets its edges from it, never by hand."""
    if context.method_name != "create" or _FROM_REQUIREMENT.get():
        return
    child = context.kwarg("child_hook_id", default=None)
    if not child:
        return
    hooks = HookManager(requester_id=context.manager.requester.id, model_registry=context.manager.model_registry)
    try:
        if getattr(hooks.get(id=child), "requires", None):
            raise HTTPException(status_code=422, detail="That hook's requirement is an expression: edit it there")
    except HTTPException as error:
        if error.status_code == 422:
            raise


# ---------------------------------------------------------------------------
# Dispositions and relation influences (W56, from dh-campaign's tracker)
# ---------------------------------------------------------------------------


def _target_kind(value: Any) -> Any:
    if value not in DISPOSITION_TARGETS:
        raise ValueError(f"A disposition's target is one of: {', '.join(DISPOSITION_TARGETS)}")
    return value


def _intensity(value: Any) -> Any:
    if value is not None and not -1 <= value <= 1:
        raise ValueError("Attitude is -1 to +1")
    return value


class DispositionModel(ApplicationModel.Optional, UpdateMixinModel.Optional, PersonModel.Reference.Optional, metaclass=ModelMeta):
    Manager: ClassVar[Type["DispositionManager"]] = None
    target_kind: Optional[str] = Field(None, description="party, person or faction")
    target_person_id: Optional[str] = Field(None, description="FK → persons.id, when the target is a person")
    target_faction_id: Optional[str] = Field(None, description="FK → factions.id, when the target is an organisation")
    attitude: Optional[str] = Field(None, description="contract/wiki.json attitudes, or a nuance of one")
    is_default: Optional[bool] = Field(False, description="The baseline toward this target")
    trigger_hook_id: Optional[str] = Field(None, description="FK → hooks.id; this attitude holds once that hook resolves")
    note: Optional[str] = Field(None)
    table_comment: ClassVar[str] = "How a person regards the party, a person or an organisation, and what changes it."

    class Create(BaseModel, PersonModel.Reference.ID):
        target_kind: str = Field(...)
        target_person_id: Optional[str] = None
        target_faction_id: Optional[str] = None
        attitude: str = Field(...)
        is_default: bool = False
        trigger_hook_id: Optional[str] = None
        note: Optional[str] = None

        _kind = field_validator("target_kind")(_target_kind)
        _attitude = field_validator("attitude")(checked_attitude)

        @model_validator(mode="after")
        def _one_target(self) -> Any:
            wanted = {"party": (None, None), "person": ("x", None), "faction": (None, "x")}[self.target_kind]
            have = ("x" if self.target_person_id else None, "x" if self.target_faction_id else None)
            if have != wanted:
                raise ValueError("Name the target that matches target_kind: a person, an organisation, or neither for the party")
            if self.is_default == bool(self.trigger_hook_id):
                raise ValueError("An entry is either the default or has a trigger hook")
            return self

    class Update(BaseModel):
        attitude: Optional[str] = None
        note: Optional[str] = None

        _attitude = field_validator("attitude")(checked_attitude)

    class Search(ApplicationModel.Search, PersonModel.Reference.ID.Search):
        target_kind: Optional[StringSearchModel] = None
        target_person_id: Optional[StringSearchModel] = None
        target_faction_id: Optional[StringSearchModel] = None
        trigger_hook_id: Optional[StringSearchModel] = None


class DispositionManager(AbstractBLLManager, RouterMixin):
    _model = DispositionModel


DispositionModel.Manager = DispositionManager


@hook_bll(DispositionManager, timing=HookTiming.BEFORE, priority=10)
def _one_default_per_target(context: HookContext) -> None:
    if context.method_name != "create" or not context.kwarg("is_default", default=False):
        return
    same = {
        "person_id": context.kwarg("person_id"),
        "target_kind": context.kwarg("target_kind"),
        "target_person_id": context.kwarg("target_person_id"),
        "target_faction_id": context.kwarg("target_faction_id"),
    }
    rows = context.manager.list(person_id=same["person_id"], target_kind=same["target_kind"]) or []
    if any(row.is_default and row.target_person_id == same["target_person_id"] and row.target_faction_id == same["target_faction_id"] for row in rows):
        raise HTTPException(status_code=422, detail="That person already has a default attitude toward that target")


class RelationInfluenceModel(ApplicationModel.Optional, UpdateMixinModel.Optional, RelationshipModel.Reference.Optional, HookModel.Reference.Optional, metaclass=ModelMeta):
    Manager: ClassVar[Type["RelationInfluenceManager"]] = None
    to_intensity: Optional[float] = Field(None, description="The relation's attitude once the hook resolves (-1 to +1)")
    note: Optional[str] = Field(None)
    table_comment: ClassVar[str] = "A hook that changes a relation's attitude when it resolves."

    class Create(BaseModel, RelationshipModel.Reference.ID, HookModel.Reference.ID):
        to_intensity: float = Field(...)
        note: Optional[str] = None

        _to = field_validator("to_intensity")(_intensity)

    class Update(BaseModel):
        to_intensity: Optional[float] = None
        note: Optional[str] = None

        _to = field_validator("to_intensity")(_intensity)

    class Search(ApplicationModel.Search, RelationshipModel.Reference.ID.Search, HookModel.Reference.ID.Search):
        pass


class RelationInfluenceManager(AbstractBLLManager, RouterMixin):
    _model = RelationInfluenceModel


RelationInfluenceModel.Manager = RelationInfluenceManager


# PersonModel and FactionModel are imported so author_person_id, giver_person_id and giver_faction_id
# get their foreign keys (genealogy and world_social are dependencies).
__all__ = [
    "JournalModel",
    "HookModel",
    "HookDependencyModel",
    "PersonHookModel",
    "FactionHookModel",
    "DispositionModel",
    "RelationInfluenceModel",
    "PersonModel",
    "FactionModel",
]
