# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 008: aliases and keywords on persons, locations, factions, items, journals and hooks,
and a person's AI voice (S4c), each JSON text. Inspector-guarded: present columns are kept."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_rpg_core_names_voice"
down_revision: Union[str, None] = "007_rpg_core_templates_kits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("persons", "locations", "factions", "items", "journals", "hooks")
COLUMNS = (
    ("aliases", "Other names it goes by, as JSON text (S4c)"),
    ("keywords", "What else wakes it in the AI's lorebook, as JSON text (S4c)"),
)
VOICE = "How the AI plays them: personality, speech, first_message, examples, as JSON text (S4c; GM-facing)"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in TABLES:
        if table not in tables:
            continue
        present = {column["name"] for column in inspector.get_columns(table)}
        wanted = [*COLUMNS, *((("voice", VOICE),) if table == "persons" else ())]
        missing = [(name, comment) for name, comment in wanted if name not in present]
        if missing:
            with op.batch_alter_table(table) as batch:
                for name, comment in missing:
                    batch.add_column(sa.Column(name, sa.String(), nullable=True, comment=comment))


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            if table == "persons":
                batch.drop_column("voice")
            for name, _comment in reversed(COLUMNS):
                batch.drop_column(name)
