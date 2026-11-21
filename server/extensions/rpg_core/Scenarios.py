# SPDX-License-Identifier: AGPL-3.0-or-later
"""Copy on start (operator, 2026-11-21): a scenario is a campaign play never edits; starting one
instantiates it into a new campaign, a playthrough, with its own copy of every record and relation.

``instantiate_campaign`` copies, under the requester's access, the campaign's places,
organisations, people, items, journals (its framing note too), hooks, tags and statuses, then every
link between them (relationships and their influences, hook dependencies and who holds which hook,
dispositions, tags and statuses on a record, item instances and what carries them, posts,
properties and pictures). Each copy's fields are its source's, with every value that names a copied
record (a reference, or an id inside JSON text: an entry's mentions, a hook's requirement) turned to
that record's copy. A value naming anything else (the setting's canon, an uploaded asset) stays: the
setting's canon is shared and never copied. Creates go a record type at a time (plural creates); a
reference to a record not yet copied is filled in a second pass. Templates stay with the scenario.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional

# What a copy never takes: identity, being a template, the owner (the copy is the requester's), and
# a hook's resolution (a playthrough starts it fresh).
NOT_COPIED = {"id", "is_template", "user_id", "resolved_at", "resolved_journal_id", "is_scenario", "scenario_id"}
# A value a later pass fills: it names a record that isn't copied yet.
_LATER = object()


@dataclass
class Copying:
    """The ids copied so far (source → copy), and every id that will be copied."""

    id_map: dict[str, str] = field(default_factory=dict)
    pending: set[str] = field(default_factory=set)
    # (manager, source row, copy id, the fields left for the second pass)
    deferred: list[tuple[Any, Any, str, list[str]]] = field(default_factory=list)
    # Everything made so far, in order (manager, id), so a failed start can be undone.
    made: list[tuple[Any, str]] = field(default_factory=list)


def _walk(value: Any, copying: Copying) -> Any:
    """A JSON value with every copied id turned to its copy; _LATER when one isn't copied yet."""
    if isinstance(value, str):
        if value in copying.id_map:
            return copying.id_map[value]
        return _LATER if value in copying.pending else value
    if isinstance(value, list):
        walked = [_walk(one, copying) for one in value]
        return _LATER if any(one is _LATER for one in walked) else walked
    if isinstance(value, dict):
        walked_dict = {key: _walk(one, copying) for key, one in value.items()}
        return _LATER if any(one is _LATER for one in walked_dict.values()) else walked_dict
    return value


def remapped(value: Any, copying: Copying) -> Any:
    """A field's value for the copy: a copied id turned to its copy, the same inside JSON text."""
    if isinstance(value, str):
        text = value.strip()
        # JSON text: an object, a list, or a string ('"<id>"', a hook's single requirement).
        if text[:1] in ("{", "[", '"') and (copying.pending & set(_strings(text)) or copying.id_map.keys() & set(_strings(text))):
            try:
                loaded = json.loads(text)
            except json.JSONDecodeError:
                return value
            walked = _walk(loaded, copying)
            return walked if walked is _LATER else json.dumps(walked, ensure_ascii=False)
        return _walk(value, copying)
    return value


def _strings(text: str) -> list[str]:
    """The quoted strings in JSON text (a cheap test for ids before parsing it)."""
    return [part for index, part in enumerate(text.split('"')) if index % 2 == 1]


def fields_of(manager: Any, row: Any, copying: Copying) -> tuple[dict[str, Any], list[str]]:
    """A row's writable fields for its copy, and the names left for the second pass."""
    writable = set(manager._model.Create.model_fields)
    fields: dict[str, Any] = {}
    later: list[str] = []
    for name, value in row.model_dump().items():
        if name not in writable or name in NOT_COPIED or value is None:
            continue
        copied = remapped(value, copying)
        if copied is _LATER:
            later.append(name)
        else:
            fields[name] = copied
    return fields, later


# The most entities one plural create takes (server-framework's MAX_BATCH_SIZE).
BATCH = 100


def create_all(manager: Any, entities: list[dict[str, Any]]) -> list[Any]:
    """Every entity made, in plural creates of at most BATCH each, in the order given."""
    made: list[Any] = []
    for start in range(0, len(entities), BATCH):
        created = manager.create(entities=entities[start : start + BATCH])
        made.extend(created if isinstance(created, list) else [created])
    return made


def copy_rows(manager: Any, rows: list[Any], copying: Copying, fixed: Optional[dict[str, Any]] = None) -> list[Any]:
    """The rows' copies, in one plural create (each runs the manager's hooks, as one create does, since
    server-framework a5121fa8; attachments too since a9ef4366); each source id now names its copy."""
    if not rows:
        return []
    prepared = [fields_of(manager, row, copying) for row in rows]
    entities = [{**fields, **(fixed or {})} for fields, _later in prepared]
    made = create_all(manager, entities)
    copying.made.extend((manager, str(copy.id)) for copy in made)
    for row, copy, (_fields, later) in zip(rows, made, prepared):
        copying.id_map[str(row.id)] = str(copy.id)
        if later:
            copying.deferred.append((manager, row, str(copy.id), later))
    return made


def finish(copying: Copying) -> None:
    """The second pass: each reference to a record copied after its own, filled in."""
    for manager, row, copy_id, later in copying.deferred:
        dumped = row.model_dump()
        changes = {name: remapped(dumped[name], copying) for name in later}
        changes = {name: value for name, value in changes.items() if value is not _LATER}
        if changes:
            manager.update(id=copy_id, **changes)


def undo(copying: Copying) -> None:
    """A failed start taken back: everything it made deleted, newest first (the campaign last), so
    no half-copied playthrough is left behind. A delete that fails is passed over: the rest go."""
    for manager, made_id in reversed(copying.made):
        try:
            manager.delete(id=made_id)
        except Exception:  # noqa: BLE001 - best effort: the start's own error is the one to report
            continue


def touching(manager: Any, anchors: tuple[str, ...], ids: list[str]) -> list[Any]:
    """A link table's rows whose anchors name any of ``ids``, each once."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    if not ids:
        return []
    seen: dict[str, Any] = {}
    for anchor in anchors:
        for row in manager.list(filters=[FieldComparison(manager.Model, anchor, "in", ids)]) or []:
            seen.setdefault(str(row.id), row)
    return list(seen.values())

