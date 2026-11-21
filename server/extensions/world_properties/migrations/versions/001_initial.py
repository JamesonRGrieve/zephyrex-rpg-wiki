# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial migration for world_properties: ``property_kits``. Their campaign_id and setting_id are
rpg_core's (rpg_core's 007 adds them). Inspector-guarded, like the framework's 001s.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_world_properties_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("ext_world_properties",)
# No depends_on: each extension has its own Alembic history; ordering is by EXT_Dependency and FKs.
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "world_properties"}


def upgrade() -> None:
    if "property_kits" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "property_kits",
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("properties", sa.String(), nullable=True, comment="The kit's keys as JSON: [{key, value_type, default, is_private, ordinal}]"),
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
        sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by_user_id", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="A property kit (W4): keys with types and defaults, applied to any record's properties.",
        info=TABLE_INFO,
    )
    op.create_index("ix_property_kits_deleted_at", "property_kits", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_property_kits_deleted_at", table_name="property_kits")
    op.drop_table("property_kits")
