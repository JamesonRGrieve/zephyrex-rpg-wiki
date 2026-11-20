# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial migration for world_social: owns the ``factions`` table. Its campaign_id column is
rpg_core's (rpg_core's 001 adds it). Inspector-guarded, like the framework's 001s.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_world_social_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("ext_world_social",)
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "world_social"}


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


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


def upgrade() -> None:
    if not _has_table("factions"):
        op.create_table(
            "factions",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("parent_id", sa.String(), sa.ForeignKey("factions.id"), nullable=True, comment="Optional foreign key to FactionModel"),
            sa.Column("kind", sa.String(), nullable=True, comment="contract/wiki.json faction_kinds"),
            sa.Column("entry", sa.String(), nullable=True, comment="The entry: a Plate value as JSON text"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="An organisation or family, under its parent (parent_id).",
            info=TABLE_INFO,
        )
        op.create_index("ix_factions_deleted_at", "factions", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_factions_deleted_at", table_name="factions")
    op.drop_table("factions")
