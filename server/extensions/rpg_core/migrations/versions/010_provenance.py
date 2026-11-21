# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 010: provenance and source on campaigns and on persons, locations, factions, items,
journals and hooks (operator, 2026-11-21: official scenarios are parsed in for personal use, and
their entities with them). Everything so far is homebrew. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_rpg_core_provenance"
down_revision: Union[str, None] = "009_rpg_core_lore"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = ("campaigns", "persons", "locations", "factions", "items", "journals", "hooks")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in TABLES:
        if table not in tables:
            continue
        present = {column["name"] for column in inspector.get_columns(table)}
        with op.batch_alter_table(table) as batch:
            if "provenance" not in present:
                batch.add_column(sa.Column("provenance", sa.String(), nullable=True, comment="homebrew, official or adapted"))
            if "source" not in present:
                batch.add_column(sa.Column("source", sa.String(), nullable=True, comment="The official title, publisher and product or page"))
        op.execute(f"UPDATE {table} SET provenance = 'homebrew' WHERE provenance IS NULL")


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("source")
            batch.drop_column("provenance")
