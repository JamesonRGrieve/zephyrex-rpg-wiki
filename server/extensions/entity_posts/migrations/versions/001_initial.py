# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial migration for entity_posts: owns ``entity_posts``. Its target is polymorphic, so no FK on
it. Inspector-guarded, like the framework's 001s.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_entity_posts_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("ext_entity_posts",)
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "entity_posts"}


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
    if not _has_table("entity_posts"):
        op.create_table(
            "entity_posts",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("target_entity_type", sa.String(), nullable=True, comment="contract/wiki.json entity_types"),
            sa.Column("target_entity_id", sa.String(), nullable=True, comment="The entity's id, in its own table"),
            sa.Column("entry", sa.String(), nullable=True, comment="The entry: a Plate value as JSON text"),
            sa.Column("position", sa.String(), nullable=True, comment="contract/wiki.json post_positions"),
            sa.Column("ordinal", sa.Integer(), nullable=True, comment="Order within its position"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A post on any entity; pinned_top first. Visibility is acl_rbac's (W9).",
            info=TABLE_INFO,
        )
        op.create_index("ix_entity_posts_deleted_at", "entity_posts", ["deleted_at"])
        op.create_index("ix_entity_posts_target", "entity_posts", ["target_entity_type", "target_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_entity_posts_target", table_name="entity_posts")
    op.drop_index("ix_entity_posts_deleted_at", table_name="entity_posts")
    op.drop_table("entity_posts")
