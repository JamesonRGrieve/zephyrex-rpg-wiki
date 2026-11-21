# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial migration for world_taxonomy: ``taxons``, ``entity_taxons``, ``statuses``,
``entity_statuses``. Their campaign_id is rpg_core's (rpg_core's 004 adds it). Inspector-guarded,
like the framework's 001s.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_world_taxonomy_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("ext_world_taxonomy",)
# No depends_on: each extension has its own Alembic history; ordering is by EXT_Dependency and FKs.
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "world_taxonomy"}


def _audit_columns() -> list:
    return [
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
        sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by_user_id", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    ]


def _target_columns() -> list:
    return [
        sa.Column("target_entity_type", sa.String(), nullable=True, comment="contract/wiki.json entity_types"),
        sa.Column("target_entity_id", sa.String(), nullable=True, comment="The record's id"),
    ]


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "taxons" not in tables:
        op.create_table(
            "taxons",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("parent_id", sa.String(), sa.ForeignKey("taxons.id"), nullable=True, comment="Optional foreign key to the parent taxon"),
            sa.Column("kind", sa.String(), nullable=True, comment="contract/wiki.json taxon_kinds"),
            sa.Column("colour", sa.String(), nullable=True, comment="#rrggbb"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A tag, category, race, species, culture, religion or other classification, in a tree.",
            info=TABLE_INFO,
        )
        op.create_index("ix_taxons_deleted_at", "taxons", ["deleted_at"])
    if "entity_taxons" not in tables:
        op.create_table(
            "entity_taxons",
            sa.Column("taxon_id", sa.String(), sa.ForeignKey("taxons.id", ondelete="CASCADE"), nullable=True, comment="Optional foreign key to TaxonModel"),
            *_target_columns(),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("taxon_id", "target_entity_type", "target_entity_id", name="uq_entity_taxons_taxon_target"),
            comment="A taxon on a record (polymorphic); once per taxon and record.",
            info=TABLE_INFO,
        )
        op.create_index("ix_entity_taxons_target", "entity_taxons", ["target_entity_type", "target_entity_id"])
    if "statuses" not in tables:
        op.create_table(
            "statuses",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("kind", sa.String(), nullable=True, comment="contract/wiki.json status_kinds"),
            sa.Column("colour", sa.String(), nullable=True, comment="#rrggbb"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A status a record can be in.",
            info=TABLE_INFO,
        )
    if "entity_statuses" not in tables:
        op.create_table(
            "entity_statuses",
            sa.Column("status_id", sa.String(), sa.ForeignKey("statuses.id", ondelete="CASCADE"), nullable=True, comment="Optional foreign key to StatusModel"),
            *_target_columns(),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("target_entity_type", "target_entity_id", name="uq_entity_statuses_target"),
            comment="A record's status (polymorphic); one per record.",
            info=TABLE_INFO,
        )


def downgrade() -> None:
    for table in ("entity_statuses", "statuses", "entity_taxons"):
        op.drop_table(table)
    op.drop_index("ix_taxons_deleted_at", table_name="taxons")
    op.drop_table("taxons")
