# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial migration for rpg_core: owns ``campaigns``, and adds the columns it
injects with @extension_model onto other extensions' tables, with real foreign keys (operator,
2026-11-20): onto genealogy's ``persons`` (kind, campaign_id, user_id, location_id, entry), and
campaign_id onto world_spatial's ``locations``, world_social's ``factions`` and world_inventory's
``items``. Game systems are zephyrex-vtt's rpg_systems. It runs after those extensions' migrations
(the framework orders by required EXT_Dependency and FKs), so every table it touches exists. Inspector guards make each step a no-op where the
table or column is already there.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_rpg_core_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("ext_rpg_core",)
# No depends_on: each extension has its own Alembic history, so another extension's revision can't
# be named. The framework runs this after genealogy and the three world_* extensions, from
# rpg_core's required EXT_Dependency on each (EXT_RPGCore.py) and its FKs into their tables.
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "rpg_core"}

# (table, column, type, foreign key target or None, comment): what rpg_core adds to other tables.
INJECTED: list[tuple[str, str, sa.types.TypeEngine, Union[str, None], str]] = [
    ("persons", "kind", sa.String(), None, "contract/wiki.json person_kinds"),
    ("persons", "campaign_id", sa.String(), "campaigns.id", "Optional foreign key to CampaignModel"),
    ("persons", "user_id", sa.String(), "users.id", "The player; none for an NPC"),
    ("persons", "location_id", sa.String(), "locations.id", "Where they are"),
    ("persons", "entry", sa.String(), None, "The entry: a Plate value as JSON text"),
    ("locations", "campaign_id", sa.String(), "campaigns.id", "Optional foreign key to CampaignModel"),
    ("factions", "campaign_id", sa.String(), "campaigns.id", "Optional foreign key to CampaignModel"),
    ("items", "campaign_id", sa.String(), "campaigns.id", "Optional foreign key to CampaignModel"),
]


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


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_table("campaigns"):
        op.create_table(
            "campaigns",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A world: the top-level container every record scopes to. user_id = its owner.",
            info=TABLE_INFO,
        )
        op.create_index("ix_campaigns_deleted_at", "campaigns", ["deleted_at"])
    for table, column, kind, target, comment in INJECTED:
        if not _has_table(table) or column in _columns(table):
            continue
        # batch mode: SQLite can't add a column with a foreign key in place; Alembic copies the table.
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column(column, kind, nullable=True, comment=comment))
            if target is not None:
                batch.create_foreign_key(f"fk_{table}_{column}_{target.split('.')[0]}", target.split(".")[0], [column], ["id"])


def downgrade() -> None:
    for table, column, _kind, target, _comment in reversed(INJECTED):
        with op.batch_alter_table(table) as batch:
            if target is not None:
                batch.drop_constraint(f"fk_{table}_{column}_{target.split('.')[0]}", type_="foreignkey")
            batch.drop_column(column)
    op.drop_index("ix_campaigns_deleted_at", table_name="campaigns")
    op.drop_table("campaigns")
