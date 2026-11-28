# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 024: a person's invariants (operator, 2026-11-28: NPCs get character invariants, lines
they never cross, "never harms a child", "never breaks a sworn oath"): a list of short sentences as
JSON text, which rpg-ai puts in their turn as hard limits. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024_rpg_core_invariants"
down_revision: Union[str, None] = "023_rpg_core_known_to_party"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "invariants" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("persons")}:
        with op.batch_alter_table("persons") as batch:
            batch.add_column(sa.Column("invariants", sa.String(), nullable=True, comment="The lines they never cross, a list of short sentences as JSON text"))


def downgrade() -> None:
    with op.batch_alter_table("persons") as batch:
        batch.drop_column("invariants")
