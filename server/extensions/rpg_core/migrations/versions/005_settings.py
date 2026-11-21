# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 005: settings (S6). ``settings`` (the universe campaigns take place in), each campaign's
``setting_id``, and on every world table ``setting_id`` (with no campaign: the setting's canon) and
``canon_level``, with real foreign keys. Inspector-guarded: present tables and columns are kept."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_rpg_core_settings"
down_revision: Union[str, None] = "004_rpg_core_taxonomy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "rpg_core"}
WORLD_TABLES = ("persons", "locations", "factions", "items", "journals", "hooks", "taxons", "statuses")


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


def _columns(inspector: sa.engine.reflection.Inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "settings" not in tables:
        op.create_table(
            "settings",
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("entry", sa.String(), nullable=True, comment="Its tone and vocabulary: a Plate value as JSON text"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A setting: the universe campaigns take place in; its canon is its campaign-less records.",
            info=TABLE_INFO,
        )
    if "campaigns" in tables and "setting_id" not in _columns(inspector, "campaigns"):
        with op.batch_alter_table("campaigns") as batch:
            batch.add_column(sa.Column("setting_id", sa.String(), nullable=True, comment="Optional foreign key to SettingModel"))
            batch.create_foreign_key("fk_campaigns_setting_id_settings", "settings", ["setting_id"], ["id"])
    for table in WORLD_TABLES:
        if table not in tables:
            continue
        present = _columns(inspector, table)
        with op.batch_alter_table(table) as batch:
            if "setting_id" not in present:
                batch.add_column(sa.Column("setting_id", sa.String(), nullable=True, comment="With no campaign: the setting's canon"))
                batch.create_foreign_key(f"fk_{table}_setting_id_settings", "settings", ["setting_id"], ["id"])
            if "canon_level" not in present:
                batch.add_column(sa.Column("canon_level", sa.String(), nullable=True, comment="contract/wiki.json canon_levels"))


def downgrade() -> None:
    for table in WORLD_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"fk_{table}_setting_id_settings", type_="foreignkey")
            batch.drop_column("canon_level")
            batch.drop_column("setting_id")
    with op.batch_alter_table("campaigns") as batch:
        batch.drop_constraint("fk_campaigns_setting_id_settings", type_="foreignkey")
        batch.drop_column("setting_id")
    op.drop_table("settings")
