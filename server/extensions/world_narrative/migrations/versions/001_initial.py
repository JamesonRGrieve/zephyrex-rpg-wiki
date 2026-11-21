# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial migration for world_narrative: owns ``journals`` (after genealogy and world_spatial,
whose persons and locations a journal names). Its campaign_id is rpg_core's (rpg_core's 002 adds it).
Inspector-guarded, like the framework's 001s.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_world_narrative_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("ext_world_narrative",)
# No depends_on: each extension has its own Alembic history; ordering is by EXT_Dependency and FKs.
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "world_narrative"}


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
    if not _has_table("journals"):
        op.create_table(
            "journals",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("kind", sa.String(), nullable=True, comment="contract/wiki.json journal_kinds"),
            sa.Column("entry", sa.String(), nullable=True, comment="The entry: a Plate value as JSON text"),
            sa.Column("location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=True, comment="Optional foreign key to LocationModel"),
            sa.Column("author_person_id", sa.String(), sa.ForeignKey("persons.id"), nullable=True, comment="Optional foreign key to PersonModel"),
            sa.Column("session_number", sa.Integer(), nullable=True, comment="For a session report: which session"),
            sa.Column("occurred_at", sa.DateTime(), nullable=True, comment="When what it records happened"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A journal: session report, diary, lore, handout, note, manuscript, prose or chapter.",
            info=TABLE_INFO,
        )
        op.create_index("ix_journals_deleted_at", "journals", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_journals_deleted_at", table_name="journals")
    op.drop_table("journals")
