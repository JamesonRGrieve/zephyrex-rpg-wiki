# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 009: a record's lorebook activation (S4d), SillyTavern World Info's fields as JSON text,
on persons, locations, factions, items, journals and hooks. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_rpg_core_lore"
down_revision: Union[str, None] = "008_rpg_core_names_voice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("persons", "locations", "factions", "items", "journals", "hooks")
COMMENT = "Its lorebook activation (SillyTavern World Info's fields), as JSON text (S4d)"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in TABLES:
        if table in tables and "lore" not in {column["name"] for column in inspector.get_columns(table)}:
            with op.batch_alter_table(table) as batch:
                batch.add_column(sa.Column("lore", sa.String(), nullable=True, comment=COMMENT))


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("lore")
