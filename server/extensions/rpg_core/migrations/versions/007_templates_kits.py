# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 007: templates and property kits' scope (S4b).

``is_template`` on persons, locations, factions, items, journals and hooks (W7: copied into
campaigns, never a world fact), and on world_properties' ``property_kits`` the ``campaign_id`` and
``setting_id`` rpg_core scopes them by, with real foreign keys. Inspector-guarded: present columns
are kept.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_rpg_core_templates_kits"
down_revision: Union[str, None] = "006_rpg_core_setting_slugs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_TABLES = ("persons", "locations", "factions", "items", "journals", "hooks")
KIT_SCOPE = (("campaign_id", "campaigns", "For one campaign; none = for any"), ("setting_id", "settings", "For one setting's records"))


def _columns(inspector: sa.engine.reflection.Inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in TEMPLATE_TABLES:
        if table in tables and "is_template" not in _columns(inspector, table):
            with op.batch_alter_table(table) as batch:
                batch.add_column(
                    sa.Column("is_template", sa.Boolean(), nullable=True, comment="A template (W7): copied into campaigns, never a world fact")
                )
    if "property_kits" in tables:
        present = _columns(inspector, "property_kits")
        with op.batch_alter_table("property_kits") as batch:
            for column, target, comment in KIT_SCOPE:
                if column not in present:
                    batch.add_column(sa.Column(column, sa.String(), nullable=True, comment=comment))
                    batch.create_foreign_key(f"fk_property_kits_{column}_{target}", target, [column], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("property_kits") as batch:
        for column, target, _comment in reversed(KIT_SCOPE):
            batch.drop_constraint(f"fk_property_kits_{column}_{target}", type_="foreignkey")
            batch.drop_column(column)
    for table in TEMPLATE_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("is_template")
