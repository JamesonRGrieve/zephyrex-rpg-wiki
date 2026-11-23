# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 018: a person's TTS voice (operator, 2026-11-23: "A voice per character"): the TTS
model's voice id their lines are read in; none is the default. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_rpg_core_tts_voice"
down_revision: Union[str, None] = "017_rpg_core_lore_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "tts_voice" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("persons")}:
        with op.batch_alter_table("persons") as batch:
            batch.add_column(sa.Column("tts_voice", sa.String(), nullable=True, comment="The TTS model's voice id for their lines (alloy, onyx…); none is the default"))


def downgrade() -> None:
    with op.batch_alter_table("persons") as batch:
        batch.drop_column("tts_voice")
