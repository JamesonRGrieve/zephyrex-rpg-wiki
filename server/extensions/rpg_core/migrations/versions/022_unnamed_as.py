# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 022: how a person reads to a party that doesn't know their name (operator, 2026-11-25:
"NPCs should have generic descriptions unless the player knows their name which gets replaced as
names are learned"): one short noun phrase; none falls back to one built from their species, Role
and gender. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022_rpg_core_unnamed_as"
down_revision: Union[str, None] = "021_rpg_core_campaign_backends"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "unnamed_as" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("persons")}:
        with op.batch_alter_table("persons") as batch:
            batch.add_column(sa.Column("unnamed_as", sa.String(), nullable=True, comment="How they read to a party that doesn't know their name (\"the hooded woman\"); none: built from species, Role and gender"))


def downgrade() -> None:
    with op.batch_alter_table("persons") as batch:
        batch.drop_column("unnamed_as")
