# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 012: a record's picture by link (operator, 2026-11-21: external images from fandom, wikis
and the like) on persons, locations, factions, items, journals and hooks. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_rpg_core_picture_urls"
down_revision: Union[str, None] = "011_rpg_core_play_styles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("persons", "locations", "factions", "items", "journals", "hooks")
COMMENT = "Its picture by https link, shown before an uploaded one"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in TABLES:
        if table in tables and "picture_url" not in {column["name"] for column in inspector.get_columns(table)}:
            with op.batch_alter_table(table) as batch:
                batch.add_column(sa.Column("picture_url", sa.String(), nullable=True, comment=COMMENT))


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("picture_url")
