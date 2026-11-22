# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 017: the lore index (hybrid retrieval, operator 2026-11-22, design approved).

``lore_chunks``: each record's entry cut into passages (wiki_shared/LoreIndex.chunk_entry), with
the record, its scope (campaign, setting, game system) and when it was embedded. On Postgres with
pgvector, pg_trgm and unaccent, also a full-text column, an embedding column (vector(768)) and GIN,
trigram and HNSW indexes (wiki_shared/LoreSql.py). Without them the table is still made, a warning
names what is missing, and lore_search runs on text alone until the embedding service finds them.
Inspector-guarded."""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_rpg_core_lore_chunks"
down_revision: Union[str, None] = "016_rpg_core_world_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "rpg_core"}


def upgrade() -> None:
    bind = op.get_bind()
    if "lore_chunks" not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            "lore_chunks",
            sa.Column("target_entity_type", sa.String(), nullable=True, comment="The record's type"),
            sa.Column("target_entity_id", sa.String(), nullable=True, comment="The record"),
            sa.Column("name", sa.String(), nullable=True, comment="The record's name (trigram-matched)"),
            sa.Column("campaign_id", sa.String(), nullable=True, comment="The record's campaign; none for a setting's canon"),
            sa.Column("setting_id", sa.String(), nullable=True, comment="The record's setting"),
            sa.Column("game_system_id", sa.String(), nullable=True, comment="The record's game system, when it has one"),
            sa.Column("kind", sa.String(), nullable=True, comment="The record's kind"),
            sa.Column("source", sa.String(), nullable=True, comment="Its source (a book), when it has one"),
            sa.Column("page", sa.Integer(), nullable=True, comment="The source's page, when known"),
            sa.Column("position", sa.Integer(), nullable=True, comment="The passage's place in the record, from 0"),
            sa.Column("path", sa.Text(), nullable=True, comment="JSON: the record's name, then its headings"),
            sa.Column("text", sa.Text(), nullable=True, comment="The passage"),
            sa.Column("tokens", sa.Integer(), nullable=True, comment="Its length in tokens (characters / 4)"),
            sa.Column("embedded_model", sa.String(), nullable=True, comment="The model that embedded it"),
            sa.Column("embedded_at", sa.DateTime(), nullable=True, comment="When it was embedded; none until then"),
            sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_by_user_id", sa.String(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            comment="A passage of a record, for the narrator's hybrid lore search (lore_search).",
            info=TABLE_INFO,
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("lore_chunks")}
    for column in ("target_entity_id", "campaign_id", "setting_id"):
        if f"ix_lore_chunks_{column}" not in indexes:
            op.create_index(f"ix_lore_chunks_{column}", "lore_chunks", [column])
    if bind.dialect.name == "postgresql":
        from zephyrex.extensions.wiki_shared.LoreSql import ensure_postgres_search  # type: ignore[import-not-found]

        missing = ensure_postgres_search(bind)
        if missing:
            logging.getLogger(__name__).warning("rpg_core 017: lore search runs on text alone until these exist: %s", "; ".join(missing))


def downgrade() -> None:
    for column in ("setting_id", "campaign_id", "target_entity_id"):
        op.drop_index(f"ix_lore_chunks_{column}", table_name="lore_chunks")
    op.drop_table("lore_chunks")
