# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 023: a person the party knows by name from the start (operator, 2026-11-25, of a
scenario's patron: "Presumably he hired them so they should know his name. This is campaign context
that should be in the scenario"): known_names counts them for every PC. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023_rpg_core_known_to_party"
down_revision: Union[str, None] = "022_rpg_core_unnamed_as"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "known_to_party" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("persons")}:
        with op.batch_alter_table("persons") as batch:
            batch.add_column(sa.Column("known_to_party", sa.Boolean(), nullable=True, comment="The party knows them by name from the start (a scenario's patron); none is no"))


def downgrade() -> None:
    with op.batch_alter_table("persons") as batch:
        batch.drop_column("known_to_party")
