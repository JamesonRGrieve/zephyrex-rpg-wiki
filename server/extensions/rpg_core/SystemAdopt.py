# SPDX-License-Identifier: AGPL-3.0-or-later
"""System level (operator, 2026-11-25: "The out of the box scenarios, pregens, everything with the
SRD should also be system level down to campaigns which are user level"): an account's copy of such
content, a setting with its canon (pregens among it), its scenarios and everything they hold, made
the template account's (TEMPLATE_ID) in place, and every other account's copy of the same merged
into it. The operator, 2026-11-25: "template user owned should just work out of the box permission
wise": the framework lets every account view, copy and share TEMPLATE's rows and only ROOT and
SYSTEM change them, so the server (running as SYSTEM) keeps updating the one shared copy.

``adopt_settings(model_registry, [primary, duplicate, …])``:

- **The primary** (an account's setting, or one SYSTEM authored) becomes TEMPLATE's where it lies: the setting, its canon, its
  scenarios (campaigns of it that are scenarios, not playthroughs) and every record in them, with
  each link, tag and status, holding, item instance, property, picture, known fact and move on
  them. Ids stay, so its owner's playthroughs keep every reference. Every account then reads it,
  and only the server changes it (the framework's rule for TEMPLATE's rows); starting a scenario
  makes the starter's own playthrough, as before.
- **Each duplicate** (another account's copy) is merged into it. Its records are matched to the
  primary's by kind and name: its canon to the primary's canon, its scenarios by name, then each
  scenario's records within the matching scenario. A matched record and every row hanging only on
  matched records (a duplicate link, property or picture) is removed (soft-deleted where the table
  keeps deleted rows); anything unmatched is moved in (its campaign and setting the primary's) and
  made TEMPLATE's, not lost. Every row that names a removed one (the duplicate's owner's
  playthroughs: their scenario_id, setting_id, a canon place, a scenario's template, an id inside
  an entry's JSON) is turned to the primary's.
- **Copies inside the primary** (``merge_copies``; Zephyrex RPG, 2026-11-25: on prod four accounts'
  vault_imports each wrote the seven scenarios into one setting): the primary's rows are grouped
  by author; one author's copy is kept (``keep_owner``, else the author of the earliest scenario;
  rows already SYSTEM's or TEMPLATE's go with it) and every other author's is merged into it as a
  duplicate setting's would be (matched by kind and name, references turned, the rest removed or
  moved in), the setting itself staying.
- **Other extensions** (VTT's scenes and sheets) adopt their own rows through ``register_adopt_hook``:
  each hook is called with (model_registry, setting_id, scenario_ids, id_map, dry_run) after the
  wiki's rows, and may return lines for the report.

The writes go straight to the tables (an author is the server's to set, never a request's), in one
transaction per setting, and the entity cache is cleared for every table touched. A dry run reads
and reports only. Run rebuild_world_keys and rebuild_lore_chunks afterwards for the removed rows.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
# Columns a reference never sits in (a row's own identity and its authors).
NOT_REFERENCES = {"id", "created_by_user_id", "updated_by_user_id", "deleted_by_user_id"}
CHUNK = 500

# Each hook: (model_registry, setting_id, scenario_ids, id_map, dry_run) -> lines for the report.
ADOPT_HOOKS: list[Callable[..., Any]] = []


@dataclass
class Adoption:
    """What one setting's adoption did (or, dry, would do)."""

    slug: str
    setting_id: str
    # A duplicate: the system setting it was merged into.
    merged_into: Optional[str] = None
    adopted: dict[str, int] = field(default_factory=dict)
    removed: dict[str, int] = field(default_factory=dict)
    moved: list[str] = field(default_factory=list)
    repointed: dict[str, int] = field(default_factory=dict)
    hooks: list[str] = field(default_factory=list)
    # The ids it removed (or, dry, would): never adopted after.
    doomed: set[str] = field(default_factory=set, repr=False)

    def line(self) -> str:
        def counts(found: dict[str, int]) -> str:
            return ", ".join(f"{count} {table}" for table, count in sorted(found.items())) or "nothing"

        head = f"setting {self.slug} ({self.setting_id})" + (f" merged into {self.merged_into}" if self.merged_into else " made system level")
        parts = [head, f"made TEMPLATE's: {counts(self.adopted)}"]
        if self.merged_into:
            parts.append(f"duplicates removed: {counts(self.removed)}")
            parts.append(f"moved in (no match): {', '.join(self.moved) or 'none'}")
        parts.append(f"references turned to the system copy: {counts(self.repointed)}")
        parts.extend(self.hooks)
        return "\n  ".join(parts)


def register_adopt_hook(hook: Callable[..., Any]) -> bool:
    """Add ``hook``, called after each setting's adoption with (model_registry, setting_id,
    scenario_ids, id_map, dry_run); the same hook again is not added twice: True when added."""
    from fastapi import HTTPException

    from zephyrex.extensions.rpg_core.BLL_RPGCore import _hook_key  # type: ignore[import-not-found]

    if not callable(hook):
        raise HTTPException(status_code=422, detail="An adopt hook is a function")
    key = _hook_key(hook)
    if any(held is hook or _hook_key(held) == key for held in ADOPT_HOOKS):
        return False
    ADOPT_HOOKS.append(hook)
    return True


# ---- what a setting holds -------------------------------------------------------------------


@dataclass
class Held:
    """A setting's system-level content: its scenarios, and every row of it by manager."""

    setting: Any
    scenarios: list[Any]
    # (manager, rows): records first (in _SCENARIO_RECORDS order), then what hangs on them.
    records: list[tuple[Any, list[Any]]]
    dependents: list[tuple[Any, list[Any]]]

    def ids(self) -> set[str]:
        found = {str(self.setting.id), *(str(one.id) for one in self.scenarios)}
        for _manager, rows in (*self.records, *self.dependents):
            found.update(str(row.id) for row in rows)
        return found


def _live(rows: Iterable[Any]) -> list[Any]:
    # ROOT's lists include deleted rows.
    return [row for row in rows if not getattr(row, "deleted_at", None)]


def _held(model_registry: Any, setting: Any) -> Held:
    from zephyrex.extensions.rpg_core.BLL_RPGCore import (  # type: ignore[import-not-found]
        _SCENARIO_RECORDS,
        CampaignManager,
        EntityInventoryManager,
        ItemInstanceManager,
        KnownFactManager,
        PersonMoveManager,
        _every,
        _manager,
        _scenario_links,
        _serves,
    )
    from zephyrex.extensions.rpg_core.Scenarios import touching  # type: ignore[import-not-found]
    from zephyrex.lib.Environment import env
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    root = env("ROOT_ID")
    campaigns = _manager(model_registry, root, CampaignManager)
    in_setting = _live(_every(campaigns, [FieldComparison(campaigns.Model, "setting_id", "eq", str(setting.id))]))
    # Its scenarios: playthroughs (a scenario_id) are their players' own, and stay so.
    scenarios = [row for row in in_setting if getattr(row, "is_scenario", None) and not getattr(row, "scenario_id", None)]
    scenario_ids = [str(row.id) for row in scenarios]
    records: list[tuple[Any, list[Any]]] = []
    for manager_class in _SCENARIO_RECORDS:
        manager = _manager(model_registry, root, manager_class)
        rows = _live(_every(manager, [FieldComparison(manager.Model, "campaign_id", "in", scenario_ids)])) if scenario_ids else []
        rows += [row for row in _live(_every(manager, [FieldComparison(manager.Model, "setting_id", "eq", str(setting.id))])) if not getattr(row, "campaign_id", None)]
        records.append((manager, rows))
    inside = {str(row.id) for _manager, rows in records for row in rows} | set(scenario_ids) | {str(setting.id)}
    known = _known_ids(model_registry)
    dependents: list[tuple[Any, list[Any]]] = []

    def hanging(manager: Any, fields: tuple[str, ...]) -> None:
        # A row touching the content that names nothing outside it (a playthrough's link to a canon
        # faction is the player's, and stays theirs). Rows taken in anchor the next table's (a
        # relationship's influences, after the relationships).
        rows = [row for row in _live(touching(manager, fields, sorted(inside))) if not _names_outside(row, inside, known)]
        inside.update(str(row.id) for row in rows)
        dependents.append((manager, rows))

    for manager_class, fields in _scenario_links():
        hanging(_manager(model_registry, root, manager_class), fields)
    for manager_class, fields in ((EntityInventoryManager, ("target_entity_id",)), (ItemInstanceManager, ("owner_person_id", "item_id"))):
        hanging(_manager(model_registry, root, manager_class), fields)
    if _serves(model_registry, "metadata"):
        from zephyrex.extensions.metadata.BLL_Metadata import MetadataManager  # type: ignore[import-not-found]

        hanging(_manager(model_registry, root, MetadataManager), ("target_entity_id",))
    if _serves(model_registry, "attachments"):
        from zephyrex.extensions.attachments.BLL_Attachments import AttachmentManager  # type: ignore[import-not-found]

        hanging(_manager(model_registry, root, AttachmentManager), ("target_entity_id",))
    for manager_class in (KnownFactManager, PersonMoveManager):
        manager = _manager(model_registry, root, manager_class)
        dependents.append((manager, _live(_every(manager, [FieldComparison(manager.Model, "campaign_id", "in", scenario_ids)])) if scenario_ids else []))
    return Held(setting=setting, scenarios=scenarios, records=records, dependents=dependents)


def _refs(row: Any) -> set[str]:
    """The ids a row names (its fields, and inside JSON text), but its own and its authors'."""
    return {found for name, value in row.model_dump().items() if name not in NOT_REFERENCES and isinstance(value, str) for found in UUID.findall(value)}


def _names_outside(row: Any, inside: set[str], known: set[str]) -> bool:
    """Whether a row names a wiki record (or campaign, link) that isn't the content's."""
    return bool((_refs(row) & known) - inside)


def _known_ids(model_registry: Any) -> set[str]:
    """Every scoped id a reference can name: each campaign, and each record of a campaign or a
    setting. A record of neither (SYSTEM's seeded play styles) is everyone's, so naming it never
    puts a row outside a setting's content."""
    from sqlalchemy import or_, select

    from zephyrex.extensions.rpg_core.BLL_RPGCore import _SCENARIO_RECORDS, CampaignManager, _manager  # type: ignore[import-not-found]
    from zephyrex.lib.Environment import env

    root = env("ROOT_ID")
    session = model_registry.DB.session()
    try:
        found = {str(one) for one in session.execute(select(_table(_manager(model_registry, root, CampaignManager)).c.id)).scalars()}
        for manager_class in _SCENARIO_RECORDS:
            table = _table(_manager(model_registry, root, manager_class))
            scoped = [table.c[name].is_not(None) for name in ("campaign_id", "setting_id") if name in table.c]
            if scoped:
                found.update(str(one) for one in session.execute(select(table.c.id).where(or_(*scoped))).scalars())
        return found
    finally:
        session.close()


# ---- the writes -----------------------------------------------------------------------------


def _table(manager: Any) -> Any:
    return manager.DB.__table__


def _chunks(ids: list[str]) -> Iterable[list[str]]:
    for start in range(0, len(ids), CHUNK):
        yield ids[start : start + CHUNK]


def _adopt(session: Any, table: Any, ids: list[str], system: str, dry_run: bool, touched: set[str]) -> int:
    """Rows made the shared owner's (``system``: TEMPLATE_ID; those not already): how many."""
    from sqlalchemy import func, or_, select

    made = 0
    for part in _chunks(sorted(set(ids))):
        wanted = table.c.id.in_(part) & or_(table.c.created_by_user_id.is_(None), table.c.created_by_user_id != system)
        count = int(session.execute(select(func.count()).select_from(table).where(wanted)).scalar() or 0)
        if count and not dry_run:
            session.execute(table.update().where(wanted).values(created_by_user_id=system))
            touched.add(table.name)
        made += count
    return made


def _remove(session: Any, table: Any, ids: list[str], dry_run: bool, touched: set[str]) -> int:
    """Rows removed: soft-deleted where the table keeps deleted rows, else deleted."""
    from sqlalchemy import func

    if not ids:
        return 0
    if not dry_run:
        for part in _chunks(sorted(set(ids))):
            if "deleted_at" in table.c:
                session.execute(table.update().where(table.c.id.in_(part) & table.c.deleted_at.is_(None)).values(deleted_at=func.now()))
            else:
                session.execute(table.delete().where(table.c.id.in_(part)))
        touched.add(table.name)
    return len(set(ids))


def _turned(value: Any, id_map: dict[str, str]) -> Any:
    """A column's value with every mapped id in it (the whole value, or inside JSON text) turned."""
    if not isinstance(value, str) or not value:
        return value
    if value in id_map:
        return id_map[value]
    if not any(found in id_map for found in UUID.findall(value)):
        return value
    return UUID.sub(lambda match: id_map.get(match.group(0), match.group(0)), value)


def _repoint(session: Any, table: Any, id_map: dict[str, str], skip: set[str], dry_run: bool, touched: set[str]) -> int:
    """Every row of ``table`` (but ``skip``'s) naming a mapped id, turned to name its counterpart."""
    from sqlalchemy import String, Text, select

    columns = [column for column in table.c if column.name not in NOT_REFERENCES and isinstance(column.type, (String, Text))]
    if not columns or not id_map:
        return 0
    changed = 0
    for row in session.execute(select(table.c.id, *columns)).all():
        if str(row[0]) in skip:
            continue
        updates = {}
        for index, column in enumerate(columns):
            turned = _turned(row[index + 1], id_map)
            if turned != row[index + 1]:
                updates[column.name] = turned
        if updates:
            changed += 1
            if not dry_run:
                session.execute(table.update().where(table.c.id == row[0]).values(**updates))
                touched.add(table.name)
    return changed


def _clear_cache(touched: set[str]) -> None:
    from zephyrex.logic.AbstractLogicManager.manager import _cache_sync_run, get_entity_cache

    cache = get_entity_cache()
    if cache is None:
        return
    for table in sorted(touched):
        try:
            _cache_sync_run(cache.invalidate_table(table))
        except Exception:  # noqa: BLE001 - a stale cache entry expires; the rows are right
            continue


def _every_table(model_registry: Any) -> list[Any]:
    """The wiki's tables a reference to a scenario's or a canon record can sit in."""
    from zephyrex.extensions.rpg_core.BLL_RPGCore import (  # type: ignore[import-not-found]
        _SCENARIO_RECORDS,
        CampaignManager,
        CampaignStartManager,
        EntityInventoryManager,
        ItemInstanceManager,
        KnownFactManager,
        PersonMoveManager,
        _manager,
        _scenario_links,
        _serves,
    )
    from zephyrex.lib.Environment import env

    root = env("ROOT_ID")
    classes: list[Any] = [CampaignManager, CampaignStartManager, *_SCENARIO_RECORDS, *(one for one, _fields in _scenario_links()), EntityInventoryManager, ItemInstanceManager, KnownFactManager, PersonMoveManager]
    if _serves(model_registry, "metadata"):
        from zephyrex.extensions.metadata.BLL_Metadata import MetadataManager  # type: ignore[import-not-found]

        classes.append(MetadataManager)
    if _serves(model_registry, "attachments"):
        from zephyrex.extensions.attachments.BLL_Attachments import AttachmentManager  # type: ignore[import-not-found]

        classes.append(AttachmentManager)
    return [_table(_manager(model_registry, root, one)) for one in classes]


# ---- matching a duplicate -------------------------------------------------------------------


def _by_name(rows: Iterable[Any]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for row in rows:
        found.setdefault(str(getattr(row, "name", "") or ""), row)
    return found


def _match(primary: Held, duplicate: Held) -> tuple[dict[str, str], list[tuple[Any, Any]]]:
    """The duplicate's ids → the primary's, by kind and name; and the unmatched records, each with
    what it moves to: (row, (campaign_id or None, setting_id))."""
    id_map = {str(duplicate.setting.id): str(primary.setting.id)}
    scenarios = _by_name(primary.scenarios)
    for one in duplicate.scenarios:
        twin = scenarios.get(str(one.name))
        if twin is not None:
            id_map[str(one.id)] = str(twin.id)
    unmatched: list[tuple[Any, Any]] = []
    for (manager, rows), (_same, theirs) in zip(duplicate.records, primary.records):
        # The primary's records of this kind, by (its scope, name): canon under "", else its scenario.
        named: dict[tuple[str, str], Any] = {}
        for row in theirs:
            named.setdefault((str(getattr(row, "campaign_id", None) or ""), str(row.name)), row)
        for row in rows:
            campaign = str(getattr(row, "campaign_id", None) or "")
            scope = id_map.get(campaign, "") if campaign else ""
            twin = named.get((scope, str(row.name))) if (not campaign or scope) else None
            if twin is not None:
                id_map[str(row.id)] = str(twin.id)
            else:
                unmatched.append((manager, row))
    return id_map, unmatched


def _anchored_only_to(row: Any, matched: set[str], scope: set[str]) -> bool:
    """Whether a dependent row hangs only on matched records (so the primary has its twin)."""
    named = _refs(row) & scope
    return bool(named) and named <= matched


# ---- adopting --------------------------------------------------------------------------------


def _author(row: Any) -> str:
    return str(getattr(row, "created_by_user_id", None) or "")


def _split(held: Held, keep_owner: Optional[str]) -> tuple[Held, list[tuple[str, Held]]]:
    """A setting's content by author: the copy kept (``keep_owner``'s, else the earliest scenario's
    author's; with every row of SYSTEM's, TEMPLATE's or no author) and each other author's copy, as
    a duplicate to merge into it (the same setting)."""
    from zephyrex.lib.Environment import env

    shared = {"", str(env("SYSTEM_ID")), str(env("TEMPLATE_ID"))}
    authors = {_author(row) for row in held.scenarios} | {_author(row) for _manager, rows in held.records for row in rows}
    authors -= shared
    if len(authors) < 2 and not keep_owner:
        return held, []
    if keep_owner is None:
        theirs = sorted((row for row in held.scenarios if _author(row) not in shared), key=lambda row: (str(getattr(row, "created_at", "") or ""), str(row.id)))
        keep_owner = _author(theirs[0]) if theirs else sorted(authors)[0]

    def view(wanted: Callable[[str], bool]) -> Held:
        return Held(
            setting=held.setting,
            scenarios=[row for row in held.scenarios if wanted(_author(row))],
            records=[(manager, [row for row in rows if wanted(_author(row))]) for manager, rows in held.records],
            dependents=[(manager, [row for row in rows if wanted(_author(row))]) for manager, rows in held.dependents],
        )

    kept = view(lambda author: author == keep_owner or author in shared)
    copies = [(author, view(lambda one, author=author: one == author)) for author in sorted(authors - {keep_owner})]
    return kept, copies


def adopt_settings(model_registry: Any, slugs: list[str], dry_run: bool = True, merge_copies: bool = False, keep_owner: Optional[str] = None) -> list[Adoption]:
    """The first setting made system level, each further one merged into it (see the module);
    with ``merge_copies``, the accounts' copies inside the first merged into one first."""
    from fastapi import HTTPException

    from zephyrex.extensions.rpg_core.BLL_RPGCore import SettingManager, _manager  # type: ignore[import-not-found]
    from zephyrex.lib.Environment import env

    if not slugs:
        raise HTTPException(status_code=422, detail="Name the settings: the first becomes system level")
    if len(set(slugs)) != len(slugs):
        raise HTTPException(status_code=422, detail="A setting is named once")
    # The shared copy's author: the template account (an earlier run's SYSTEM rows move to it too).
    system = env("TEMPLATE_ID")
    settings = _manager(model_registry, env("ROOT_ID"), SettingManager)
    found = []
    for slug in slugs:
        rows = _live(settings.list(slug=slug) or [])
        if not rows:
            raise HTTPException(status_code=404, detail=f"No setting has the slug {slug!r}")
        found.append(rows[0])
    primary = _held(model_registry, found[0])
    report: list[Adoption] = []
    session = model_registry.DB.session()
    touched: set[str] = set()
    try:
        # The accounts' copies inside it merged into one (merge_copies), before it is adopted.
        doomed: set[str] = set()
        if merge_copies:
            kept, copies = _split(primary, keep_owner)
            for author, copy in copies:
                merged, scenario_ids, id_map = _merge(model_registry, session, kept, copy, system, dry_run, touched, within=True)
                merged.slug = f"{found[0].slug}: {author}'s copy"
                if not dry_run:
                    session.commit()
                _clear_cache(touched)
                merged.hooks = _run_hooks(model_registry, str(found[0].id), scenario_ids, id_map, dry_run)
                report.append(merged)
                doomed |= merged.doomed
        # The primary, made TEMPLATE's where it lies.
        made = Adoption(slug=str(found[0].slug), setting_id=str(found[0].id))
        made.adopted["settings"] = _adopt(session, _table(settings), [str(found[0].id)], system, dry_run, touched)
        campaigns_table = _table(_manager(model_registry, env("ROOT_ID"), _campaign_manager()))
        made.adopted["campaigns"] = _adopt(session, campaigns_table, [str(one.id) for one in primary.scenarios if str(one.id) not in doomed], system, dry_run, touched)
        for manager, rows in (*primary.records, *primary.dependents):
            count = _adopt(session, _table(manager), [str(row.id) for row in rows if str(row.id) not in doomed], system, dry_run, touched)
            if count:
                made.adopted[_table(manager).name] = made.adopted.get(_table(manager).name, 0) + count
        if not dry_run:
            session.commit()
        _clear_cache(touched)
        made.hooks = _run_hooks(model_registry, str(found[0].id), [str(one.id) for one in primary.scenarios], {}, dry_run)
        report.append(made)
        for setting in found[1:]:
            merged, scenario_ids, id_map = _merge(model_registry, session, primary, _held(model_registry, setting), system, dry_run, touched)
            if not dry_run:
                session.commit()
            _clear_cache(touched)
            merged.hooks = _run_hooks(model_registry, str(primary.setting.id), scenario_ids, id_map, dry_run)
            report.append(merged)
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
        _clear_cache(touched)
    return report


def _campaign_manager() -> Any:
    from zephyrex.extensions.rpg_core.BLL_RPGCore import CampaignManager  # type: ignore[import-not-found]

    return CampaignManager


def _merge(model_registry: Any, session: Any, primary: Held, duplicate: Held, system: str, dry_run: bool, touched: set[str], within: bool = False) -> tuple[Adoption, list[str], dict[str, str]]:
    """One duplicate merged into the primary (see the module): what it did, the system scenarios
    after it, and its id map (the duplicate's → the primary's), for the adopt hooks. ``within``:
    an account's copy inside the primary's own setting, which stays."""
    from zephyrex.extensions.rpg_core.BLL_RPGCore import SettingManager, _manager  # type: ignore[import-not-found]
    from zephyrex.lib.Environment import env

    root = env("ROOT_ID")
    done = Adoption(slug=str(duplicate.setting.slug), setting_id=str(duplicate.setting.id), merged_into=str(primary.setting.slug))
    id_map, unmatched = _match(primary, duplicate)
    if within:
        # The one setting is both; it stays, and nothing hangs on it as a match.
        id_map.pop(str(duplicate.setting.id), None)
    scope = duplicate.ids() - ({str(duplicate.setting.id)} if within else set())
    matched = set(id_map)
    campaigns_table = _table(_manager(model_registry, root, _campaign_manager()))
    removed: dict[str, list[str]] = {}
    kept: dict[str, list[str]] = {}

    def note(found: dict[str, list[str]], table: Any, row_id: str) -> None:
        found.setdefault(table.name, []).append(row_id)

    tables: dict[str, Any] = {}
    # The duplicate's setting and its matched scenarios go; an unmatched scenario moves in whole.
    settings_table = _table(_manager(model_registry, root, SettingManager))
    tables[settings_table.name] = settings_table
    if not within:
        note(removed, settings_table, str(duplicate.setting.id))
    tables[campaigns_table.name] = campaigns_table
    for one in duplicate.scenarios:
        if str(one.id) in matched:
            note(removed, campaigns_table, str(one.id))
        else:
            note(kept, campaigns_table, str(one.id))
            done.moved.append(f"scenario {one.name} ({one.id})")
    moved_ids = {str(row.id) for _manager, row in unmatched}
    for manager, rows in duplicate.records:
        table = _table(manager)
        tables[table.name] = table
        for row in rows:
            note(kept if str(row.id) in moved_ids else removed, table, str(row.id))
    for manager, row in unmatched:
        if str(getattr(row, "campaign_id", None) or "") not in {str(one.id) for one in duplicate.scenarios if str(one.id) not in matched}:
            done.moved.append(f"{_table(manager).name} {row.name} ({row.id})")
    for manager, rows in duplicate.dependents:
        table = _table(manager)
        tables[table.name] = table
        for row in rows:
            note(removed if _anchored_only_to(row, matched, scope) else kept, table, str(row.id))
    doomed = {one for ids in removed.values() for one in ids}
    done.doomed = set(doomed)
    # Every reference to a removed row (the duplicate's moved rows, and anyone's playthroughs) turned.
    for table in _every_table(model_registry):
        count = _repoint(session, table, id_map, doomed, dry_run, touched)
        if count:
            done.repointed[table.name] = count
    for name, ids in kept.items():
        count = _adopt(session, tables[name], ids, system, dry_run, touched)
        if count:
            done.adopted[name] = count
    for name, ids in removed.items():
        done.removed[name] = _remove(session, tables[name], ids, dry_run, touched)
    scenario_ids = sorted({str(one.id) for one in primary.scenarios} | {str(one.id) for one in duplicate.scenarios if str(one.id) not in matched})
    return done, scenario_ids, id_map


def _run_hooks(model_registry: Any, setting_id: str, scenario_ids: list[str], id_map: dict[str, str], dry_run: bool) -> list[str]:
    from zephyrex.lib.Logging import logger

    lines: list[str] = []
    for hook in list(ADOPT_HOOKS):
        try:
            said = hook(model_registry, setting_id, scenario_ids, dict(id_map), dry_run)
        except Exception as error:  # noqa: BLE001 - another extension's failure is reported, not fatal
            logger.warning(f"rpg_core: an adopt hook ({getattr(hook, '__qualname__', hook)}) failed for {setting_id}: {error}")
            lines.append(f"adopt hook {getattr(hook, '__qualname__', hook)} failed: {error}")
            continue
        if isinstance(said, str):
            lines.append(said)
        elif isinstance(said, list):
            lines.extend(str(one) for one in said)
    return lines
