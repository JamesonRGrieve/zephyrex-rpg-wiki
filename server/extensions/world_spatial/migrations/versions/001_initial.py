# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial migration for world_spatial: owns the ``locations`` table (after genealogy, whose
``persons`` a place can belong to). Its campaign_id column is
rpg_core's (rpg_core's 001 adds it). The Inspector guard makes this a no-op on a database that
already has the table (from the runtime create_all fallback, before this migration existed).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_world_spatial_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("ext_world_spatial",)
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "world_spatial"}


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
    if not _has_table("locations"):
        op.create_table(
            "locations",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("parent_id", sa.String(), sa.ForeignKey("locations.id"), nullable=True, comment="Optional foreign key to LocationModel"),
            sa.Column("kind", sa.String(), nullable=True, comment="contract/wiki.json location_kinds"),
            sa.Column("entry", sa.String(), nullable=True, comment="The entry: a Plate value as JSON text"),
            sa.Column("associated_person_id", sa.String(), sa.ForeignKey("persons.id"), nullable=True, comment="Optional foreign key to PersonModel"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A place at any scale, under its parent (parent_id).",
            info=TABLE_INFO,
        )
        op.create_index("ix_locations_deleted_at", "locations", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_locations_deleted_at", table_name="locations")
    op.drop_table("locations")
