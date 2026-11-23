# SPDX-License-Identifier: AGPL-3.0-or-later
"""The narrator's hybrid lore search (operator, 2026-11-22: pgvector over the full book library;
design approved). Each record's entry is kept as passages (lore_chunks, rpg_core 017), rewritten by
the hooks that keep world_keys. lore_search ranks a campaign's passages four ways and fuses them
(wiki_shared/LoreIndex.py, contract/lore-index-cases.json):

- exact: the records world_entities_matching names, always first;
- text: Postgres full text (tsv), else the passages sharing the most of the text's words;
- trigram: the record names similar to part of the text (pg_trgm);
- vector: cosine distance to the text's embedding (pgvector, nomic-embed-text-v1.5).

Scope: the campaign's own, its scenario's, and its setting's canon of no game system or the
campaign's. What the requester may not see (another's, GM-only to a player) is dropped through
world_entities_by_id. Passages are embedded by LoreEmbeddingService in the background, never in a
request; the embedder is registered by the composing app (register_embedder) or read from
WIKI_EMBED_URL and WIKI_EMBED_MODEL."""

import asyncio
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel as PlainModel
from pydantic import Field
from sqlalchemy import bindparam, text
from zephyrex.extensions.wiki_shared.LoreIndex import chunk_entry, fuse, pack, prefixed, tokens  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.LoreSql import DIMENSION, ensure_postgres_search, search_columns  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.WorldKeys import normalised  # type: ignore[import-not-found]
from zephyrex.lib.Environment import env
from zephyrex.lib.Logging import logger
from zephyrex.logic.AbstractService import AbstractService

EMBED_BATCH = 16
RANK_DEPTH = 60
ID_BATCH = 500

Embed = Callable[[list[str]], list[list[float]]]
_registered: dict[str, Any] = {}


def register_embedder(embed: Embed, model: str) -> None:
    """The composing app's embedder (rpg-ai: its "embed"-role endpoint): texts in, vectors out."""
    _registered.update(embed=embed, model=model)


def _http_embedder(url: str, model: str) -> Embed:
    def embed(texts: list[str]) -> list[list[float]]:
        request = urllib.request.Request(
            url.rstrip("/") + "/embeddings",
            data=json.dumps({"model": model, "input": texts}).encode(),
            # bifrost wants a bearer token, any non-empty one (Self Hosted AI, 2026-11-23).
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.getenv('WIKI_EMBED_KEY') or 'wiki'}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as answer:  # noqa: S310 - the operator's endpoint
            body = json.loads(answer.read())
        return [row["embedding"] for row in sorted(body["data"], key=lambda row: row["index"])]

    return embed


def embedder() -> Optional[tuple[Embed, str]]:
    """The registered embedder, else WIKI_EMBED_URL and WIKI_EMBED_MODEL, else none."""
    if "embed" in _registered:
        return _registered["embed"], str(_registered["model"])
    url, model = os.getenv("WIKI_EMBED_URL"), os.getenv("WIKI_EMBED_MODEL")
    return (_http_embedder(url, model), model) if url and model else None


def _chunks(model_registry: Any) -> Any:
    from zephyrex.extensions.rpg_core.BLL_RPGCore import LoreChunkManager  # type: ignore[import-not-found]

    return LoreChunkManager(requester_id=env("SYSTEM_ID"), model_registry=model_registry)


def passages_of(record: Any) -> list[dict[str, Any]]:
    """A record's passages: its entry's, else its description, else its name alone."""
    name = str(getattr(record, "name", "") or "")
    found = chunk_entry(name, getattr(record, "entry", None))
    if not found:
        found = [{"path": [name], "text": str(getattr(record, "description", "") or "").strip() or name}]
    return found


def index_lore(model_registry: Any, kind: str, records: list[Any], replace: bool = True) -> int:
    """These records' passages written (their old ones dropped first when ``replace``); templates
    and deleted records have none. Returns how many were written."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison
    from zephyrex.extensions.rpg_core.Scenarios import create_all  # type: ignore[import-not-found]

    chunks = _chunks(model_registry)
    ids = [str(record.id) for record in records]
    if replace and ids:
        for start in range(0, len(ids), ID_BATCH):
            for row in chunks.list(filters=[FieldComparison(chunks.Model, "target_entity_id", "in", ids[start : start + ID_BATCH])]) or []:
                chunks.delete(id=str(row.id))
    rows = [
        {
            "target_entity_type": kind,
            "target_entity_id": str(record.id),
            "name": str(getattr(record, "name", "") or ""),
            "campaign_id": getattr(record, "campaign_id", None),
            "setting_id": getattr(record, "setting_id", None),
            "game_system_id": getattr(record, "game_system_id", None),
            "kind": getattr(record, "kind", None),
            "source": getattr(record, "source", None),
            "position": position,
            "path": json.dumps(passage["path"]),
            "text": passage["text"],
            "tokens": tokens(passage["text"]),
        }
        for record in records
        if not getattr(record, "is_template", None) and not getattr(record, "deleted_at", None)
        for position, passage in enumerate(passages_of(record))
    ]
    create_all(chunks, rows)
    return len(rows)


def rebuild_lore_chunks(model_registry: Any, requester_id: str) -> dict[str, int]:
    """The requester's records with no passages yet indexed (made before rpg_core 017); those
    already indexed stay as their hooks keep them. {kind: records indexed}."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison
    from zephyrex.extensions.rpg_core.BLL_RPGCore import WORLD_ENTITY_MANAGERS, _every, _manager  # type: ignore[import-not-found]

    chunks = _chunks(model_registry)
    indexed: dict[str, int] = {}
    for kind, manager_class in WORLD_ENTITY_MANAGERS.items():
        records = _every(_manager(model_registry, requester_id, manager_class))
        ids = [str(record.id) for record in records]
        held: set[str] = set()
        for start in range(0, len(ids), ID_BATCH):
            held.update(str(row.target_entity_id) for row in chunks.list(filters=[FieldComparison(chunks.Model, "target_entity_id", "in", ids[start : start + ID_BATCH])]) or [])
        missing = [record for record in records if str(record.id) not in held and not getattr(record, "is_template", None) and not getattr(record, "deleted_at", None)]
        index_lore(model_registry, kind, missing, replace=False)
        indexed[kind] = len(missing)
    return indexed


BOOK = "book"  # a book's passages: target_entity_type, with target_entity_id "book:<slug>"
BOOK_PAGE = "book_page"


def import_book(
    model_registry: Any,
    requester_id: str,
    setting_id: str,
    game_system_id: Optional[str],
    slug: str,
    title: str,
    pages: list[tuple[int, list[dict[str, Any]]]],
    dry_run: bool = False,
) -> int:
    """A book's pages as passages of its setting's canon (book_import, the operator's instance only):
    each page's blocks cut as a record's entry is, its path the title then its headings, its source
    the title and its page. A book imported again replaces its passages. No wiki record holds the
    text, so the world sync never carries it; lore_search finds it in scope. Returns the passages."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison
    from zephyrex.extensions.rpg_core.BLL_RPGCore import SettingManager, _manager  # type: ignore[import-not-found]
    from zephyrex.extensions.rpg_core.Scenarios import create_all  # type: ignore[import-not-found]

    _manager(model_registry, requester_id, SettingManager).get(id=setting_id)  # readable by the importer
    target = f"{BOOK}:{slug}"
    rows: list[dict[str, Any]] = []
    for page, blocks in pages:
        for passage in chunk_entry(title, blocks):
            rows.append(
                {
                    "target_entity_type": BOOK,
                    "target_entity_id": target,
                    "name": title,
                    "setting_id": setting_id,
                    "game_system_id": game_system_id,
                    "kind": BOOK_PAGE,
                    "source": title,
                    "page": page,
                    "position": len(rows),
                    "path": json.dumps(passage["path"]),
                    "text": passage["text"],
                    "tokens": tokens(passage["text"]),
                }
            )
    if dry_run:
        return len(rows)
    chunks = _chunks(model_registry)
    for row in _every_chunk(chunks, [FieldComparison(chunks.Model, "target_entity_id", "eq", target)]):
        chunks.delete(id=str(row.id))
    create_all(chunks, rows)
    return len(rows)


def _every_chunk(chunks: Any, filters: list[Any]) -> list[Any]:
    from zephyrex.extensions.rpg_core.BLL_RPGCore import _every  # type: ignore[import-not-found]

    return _every(chunks, filters)


def _vector_literal(vector: list[float]) -> str:
    if len(vector) != DIMENSION:
        raise ValueError(f"The embedder answered {len(vector)} dimensions; lore_chunks.embedding holds {DIMENSION} (nomic-embed-text-v1.5)")
    return "[" + ",".join(repr(float(one)) for one in vector) + "]"


def embed_pending(model_registry: Any, batch: int = EMBED_BATCH, since: Optional[datetime] = None) -> int:
    """One batch of passages not yet embedded, embedded (only those made after ``since``, when
    given). Returns how many (0 when there is no embedder, no embedding column, or nothing waiting)."""
    found = embedder()
    if found is None:
        return 0
    embed, model = found
    session = _chunks(model_registry).db
    try:
        if "embedding" not in search_columns(session.connection()):
            return 0
        rows = session.execute(
            text(
                "SELECT id, name, text FROM lore_chunks WHERE embedded_at IS NULL AND deleted_at IS NULL"
                + (" AND created_at >= :since" if since is not None else "")
                + " ORDER BY created_at, id LIMIT :n"
            ),
            {"n": batch, **({"since": since} if since is not None else {})},
        ).all()
        if not rows:
            return 0
        vectors = embed([prefixed(f"{row.name}: {row.text}", query=False) for row in rows])
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for row, vector in zip(rows, vectors, strict=True):
            session.execute(
                text("UPDATE lore_chunks SET embedding = CAST(:v AS vector), embedded_model = :m, embedded_at = :t WHERE id = :id"),
                {"v": _vector_literal(vector), "m": model, "t": now, "id": row.id},
            )
        session.commit()
        return len(rows)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


BACKFILL_HOURS = "1-7"  # server-local hours for the full backfill (Self Hosted AI: off-hours only)
RECENT = timedelta(hours=24)  # outside them, only passages this new: the day's pages
BACKOFF_FIRST, BACKOFF_MOST = 30.0, 600.0


def in_backfill_window(hour: int, spec: str = BACKFILL_HOURS) -> bool:
    """Whether a server-local hour is in "start-end" (end exclusive, may wrap past midnight;
    "always" or "" is every hour, "never" none)."""
    spec = (spec or "").strip().lower()
    if spec in ("", "always"):
        return True
    if spec == "never":
        return False
    start, _, end = spec.partition("-")
    first, last = int(start) % 24, int(end) % 24
    return first <= hour < last if first <= last else hour >= first or hour < last


class LoreEmbeddingService(AbstractService):
    """Embeds waiting passages one batch at a time (EMBED_BATCH, one request in flight, a pause
    between: the embed card is a GTX 970 shared with rpg-ai's decide model). The full backlog drains
    only in the backfill hours (WIKI_EMBED_BACKFILL_HOURS, server-local, default 1-7); outside them
    only the day's new passages are embedded. A failure (a 5xx, the endpoint away) backs off, 30 s
    doubling to 10 min, and never stops the loop. On its first run it makes the Postgres search parts
    where they can be made, and logs what is missing."""

    def __init__(self, requester_id: str, model_registry: Any, **kwargs: Any) -> None:
        super().__init__(requester_id=requester_id, interval_seconds=int(os.getenv("WIKI_EMBED_INTERVAL", "5")), **kwargs)
        self.model_registry = model_registry
        self._prepared = False
        self._backoff = 0.0
        self._resume_at = 0.0

    def _prepare(self) -> None:
        session = _chunks(self.model_registry).db
        try:
            missing = ensure_postgres_search(session.connection())
            session.commit()
        finally:
            session.close()
        if missing and missing[0].startswith("the "):
            logger.warning(f"Lore search runs without vectors until these exist: {'; '.join(missing)}")

    async def update(self) -> None:
        if embedder() is None or time.monotonic() < self._resume_at:
            return
        try:
            if not self._prepared:
                await asyncio.to_thread(self._prepare)
                self._prepared = True
            now = datetime.now()
            since = None if in_backfill_window(now.hour, os.getenv("WIKI_EMBED_BACKFILL_HOURS", BACKFILL_HOURS)) else (datetime.now(timezone.utc) - RECENT).replace(tzinfo=None)
            await asyncio.to_thread(embed_pending, self.model_registry, EMBED_BATCH, since)
            self._backoff = 0.0
        except Exception as error:  # noqa: BLE001 - backed off and retried, never the loop stopped
            self._backoff = min(BACKOFF_MOST, max(BACKOFF_FIRST, self._backoff * 2))
            self._resume_at = time.monotonic() + self._backoff
            logger.warning(f"Lore embedding failed; retrying in {self._backoff:.0f} s: {str(error).splitlines()[0][:200] if str(error) else type(error).__name__}")


class LoreSearchAsk(PlainModel):
    text: str = Field(..., min_length=1, max_length=20000, description="What to find lore for (a turn's text)")
    k: int = Field(20, ge=1, le=100, description="At most this many passages")
    token_budget: int = Field(2000, ge=1, le=50000, description="Their tokens at most (characters / 4)")
    kinds: Optional[list[str]] = Field(None, description="Only these record types (location, person, faction, item, journal)")
    tags: Optional[list[str]] = Field(None, description="Exact hits only with any of these tags")
    include_setting: bool = Field(True, description="The setting's canon too")


class LoreSearchEnvelope(PlainModel):
    lore_search: LoreSearchAsk


class LorePassage(PlainModel):
    id: str
    record_id: str
    record_type: str
    name: str
    path: list[str]
    text: str
    tokens: int
    source: Optional[str] = None
    page: Optional[int] = None
    score: float
    ranks: dict[str, int] = Field(..., description="Its rank by each method that found it, from 1")


class LoreSearched(PlainModel):
    passages: list[LorePassage]
    methods: dict[str, str] = Field(..., description="Each method: used, basic, or unavailable and why")


def _scope(campaign: Any, include_setting: bool) -> tuple[str, dict[str, Any]]:
    owners = [one for one in (str(campaign.id), getattr(campaign, "scenario_id", None)) if one]
    clause = "(campaign_id IN :owners"
    params: dict[str, Any] = {"owners": owners}
    setting = getattr(campaign, "setting_id", None)
    if include_setting and setting:
        clause += " OR (campaign_id IS NULL AND setting_id = :setting AND (game_system_id IS NULL"
        params["setting"] = str(setting)
        system = getattr(campaign, "game_system_id", None)
        if system:
            clause += " OR game_system_id = :system"
            params["system"] = str(system)
        clause += "))"
    return clause + ")", params


def _ranked(session: Any, sql: str, params: dict[str, Any]) -> list[str]:
    statement = text(sql).bindparams(bindparam("owners", expanding=True))
    if "kinds" in params:
        statement = statement.bindparams(bindparam("kinds", expanding=True))
    return [str(row[0]) for row in session.execute(statement, params)]


def lore_search(
    model_registry: Any,
    requester_id: str,
    campaign_id: str,
    query: str,
    k: int = 20,
    token_budget: int = 2000,
    kinds: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    include_setting: bool = True,
) -> LoreSearched:
    """The campaign's passages for ``query``, best first, at most ``k`` and ``token_budget``."""
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison
    from zephyrex.extensions.rpg_core.BLL_RPGCore import CampaignManager, _manager, era_excluded, world_entities_by_id, world_entities_matching  # type: ignore[import-not-found]

    campaign = _manager(model_registry, requester_id, CampaignManager).get(id=campaign_id)
    excluded = era_excluded(model_registry, requester_id, campaign_id) if include_setting else frozenset()
    scope, params = _scope(campaign, include_setting)
    if kinds:
        scope += " AND target_entity_type IN :kinds"
        params["kinds"] = list(kinds)
    base = f"FROM lore_chunks WHERE deleted_at IS NULL AND {scope}"
    chunks = _chunks(model_registry)
    session = chunks.db
    methods: dict[str, str] = {}
    rankings: dict[str, list[str]] = {}

    # exact: each named record's first passage, in world_entities_matching's order.
    named = world_entities_matching(model_registry, requester_id, campaign_id, query, limit=k, include_setting=include_setting, tags=tags)
    order = [entity.id for entity in named.world_entities]
    exact: list[str] = []
    if order:
        first = {
            str(row.target_entity_id): str(row.id)
            for row in chunks.list(filters=[FieldComparison(chunks.Model, "target_entity_id", "in", order), FieldComparison(chunks.Model, "position", "eq", 0)]) or []
        }
        exact = [first[one] for one in order if one in first]
    methods["exact"] = "used"

    columns = search_columns(session.connection())
    if "tsv" in columns:
        rankings["text"] = _ranked(
            session,
            f"SELECT id {base} AND tsv @@ websearch_to_tsquery('english', rpg_unaccent(:q)) "
            f"ORDER BY ts_rank(tsv, websearch_to_tsquery('english', rpg_unaccent(:q))) DESC, id LIMIT {RANK_DEPTH}",
            {**params, "q": query},
        )
        methods["text"] = "used"
        rankings["trigram"] = _ranked(session, f"SELECT id {base} AND :q %> name ORDER BY word_similarity(name, :q) DESC, id LIMIT {RANK_DEPTH}", {**params, "q": query})
        methods["trigram"] = "used"
    else:
        # No full-text index (SQLite, or Postgres without the extensions): the passages sharing the
        # most of the text's longest words.
        words = sorted({word for word in normalised(query).split() if len(word) > 3}, key=lambda word: (-len(word), word))[:8]
        if words:
            likes = " OR ".join(f"lower(text) LIKE :w{index}" for index in range(len(words)))
            candidates = session.execute(
                text(f"SELECT id, text {base} AND ({likes}) LIMIT 500").bindparams(*[bindparam(name, expanding=True) for name in ("owners", "kinds") if name in params]),
                {**params, **{f"w{index}": f"%{word}%" for index, word in enumerate(words)}},
            ).all()
            scored = sorted(((sum(word in normalised(row.text or "") for word in words), str(row.id)) for row in candidates), key=lambda pair: (-pair[0], pair[1]))
            rankings["text"] = [one for score, one in scored[:RANK_DEPTH] if score > 0]
        methods["text"] = "basic (no full-text index on this database)"
        methods["trigram"] = "unavailable: needs Postgres with pg_trgm"

    found = embedder()
    if "embedding" not in columns:
        methods["vector"] = "unavailable: needs Postgres with pgvector (rpg_core 017's columns)"
    elif found is None:
        methods["vector"] = "unavailable: no embedder registered (register_embedder, or WIKI_EMBED_URL and WIKI_EMBED_MODEL)"
    else:
        try:
            vector = _vector_literal(found[0]([prefixed(query, query=True)])[0])
            rankings["vector"] = _ranked(
                session, f"SELECT id {base} AND embedding IS NOT NULL ORDER BY embedding <=> CAST(:v AS vector), id LIMIT {RANK_DEPTH}", {**params, "v": vector}
            )
            methods["vector"] = "used"
        except Exception as error:  # noqa: BLE001 - the other methods still answer; the reason is reported
            logger.warning(f"lore_search: the embedder failed: {error}")
            methods["vector"] = f"unavailable: the embedder failed ({str(error).splitlines()[0][:200]})"

    fused = fuse(rankings, exact)
    ranks = {name: {one: index for index, one in enumerate(ids, start=1)} for name, ids in {"exact": exact, **rankings}.items()}
    ids = [one for one, _score in fused][: max(k * 3, k)]
    rows = {str(row.id): row for row in chunks.list(filters=[FieldComparison(chunks.Model, "id", "in", ids)]) or []} if ids else {}
    # What the requester may see: the records world_entities_by_id answers for them.
    records = sorted({str(row.target_entity_id) for row in rows.values() if row.target_entity_type != BOOK})
    visible: set[str] = set()
    for start in range(0, len(records), 100):
        visible.update(entity.id for entity in world_entities_by_id(model_registry, requester_id, records[start : start + 100]).world_entities)
    ordered = [
        LorePassage(
            id=one,
            record_id=str(rows[one].target_entity_id),
            record_type=str(rows[one].target_entity_type),
            name=str(rows[one].name or ""),
            path=json.loads(rows[one].path or "[]"),
            text=str(rows[one].text or ""),
            tokens=int(rows[one].tokens or 0),
            source=rows[one].source,
            page=rows[one].page,
            score=score,
            ranks={name: found_ranks[one] for name, found_ranks in ranks.items() if one in found_ranks},
        )
        for one, score in fused
        # A book's pages are canon of the setting, in scope already; a record, as its requester sees it;
        # never another era's canon.
        if one in rows
        and (rows[one].target_entity_type == BOOK or str(rows[one].target_entity_id) in visible)
        and str(rows[one].target_entity_id) not in excluded
    ]
    packed = [LorePassage.model_validate(one) for one in pack([passage.model_dump() for passage in ordered], token_budget)][:k]
    return LoreSearched(passages=packed, methods=methods)
