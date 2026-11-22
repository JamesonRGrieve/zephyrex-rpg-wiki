# SPDX-License-Identifier: AGPL-3.0-or-later
"""The lore index's Postgres parts (rpg_core 017 and the embedding service share them): the
extensions it needs (pgvector, pg_trgm, unaccent), a full-text column, the embedding column and
their indexes. Idempotent; on another database, or without the extensions, nothing is changed and
what is missing is named, so lore_search says why it runs on text alone."""

from typing import Any

from sqlalchemy import text

DIMENSION = 768  # nomic-embed-text-v1.5 (Zephyrex RPG, from prod's "embed" endpoint)
EXTENSIONS = ("vector", "pg_trgm", "unaccent")

DDL = (
    # unaccent is only STABLE; a generated column needs an IMMUTABLE wrapper.
    "CREATE OR REPLACE FUNCTION rpg_unaccent(text) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT "
    "AS $$ SELECT unaccent('unaccent'::regdictionary, $1) $$",
    "ALTER TABLE lore_chunks ADD COLUMN IF NOT EXISTS tsv tsvector GENERATED ALWAYS AS "
    "(to_tsvector('english', rpg_unaccent(coalesce(name, '') || ' ' || coalesce(text, '')))) STORED",
    f"ALTER TABLE lore_chunks ADD COLUMN IF NOT EXISTS embedding vector({DIMENSION})",
    "CREATE INDEX IF NOT EXISTS ix_lore_chunks_tsv ON lore_chunks USING gin (tsv)",
    "CREATE INDEX IF NOT EXISTS ix_lore_chunks_name_trgm ON lore_chunks USING gin (name gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_lore_chunks_embedding ON lore_chunks USING hnsw (embedding vector_cosine_ops)",
)


def ensure_postgres_search(connection: Any) -> list[str]:
    """The extensions, columns and indexes made where they can be; returns what is missing (empty
    when ready). Each step runs in a savepoint, so a refusal never spoils the caller's transaction."""
    if connection.dialect.name != "postgresql":
        return [f"a Postgres database (this is {connection.dialect.name})"]
    available = {row[0] for row in connection.execute(text("SELECT name FROM pg_available_extensions"))}
    missing = [name for name in EXTENSIONS if name not in available]
    if missing:
        return [f"the {name} extension (not installed on the server)" for name in missing]
    for name in EXTENSIONS:
        try:
            with connection.begin_nested():
                connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {name}"))
        except Exception as error:  # noqa: BLE001 - named back to the caller, never swallowed
            missing.append(f"the {name} extension (could not be created: {str(error).splitlines()[0]})")
    if missing:
        return missing
    for statement in DDL:
        try:
            with connection.begin_nested():
                connection.execute(text(statement))
        except Exception as error:  # noqa: BLE001
            return [f"the lore index's columns ({str(error).splitlines()[0]})"]
    return []


def search_columns(connection: Any) -> set[str]:
    """Which of the Postgres-only columns lore_chunks has (tsv, embedding)."""
    if connection.dialect.name != "postgresql":
        return set()
    rows = connection.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'lore_chunks' AND column_name IN ('tsv', 'embedding')")
    )
    return {row[0] for row in rows}
