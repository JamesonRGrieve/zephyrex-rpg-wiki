# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_social 002: genealogy's ``relationships`` gain organisation endpoints (``faction_id``,
``target_faction_id``), a ``colour`` and a ``mirror_relationship_id`` (W5), with real foreign keys.
One endpoint a side is the BLL's rule (a 422), not a CHECK: genealogy's existing rows are left as
they are. Inspector-guarded: a column already there (vtt's rpg_state made the faction endpoints by
create_all) is kept, and only the missing ones are added.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_world_social_relations"
down_revision: Union[str, None] = "001_world_social_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = (
    ("faction_id", "factions", "fk_relationships_faction_id_factions"),
    ("target_faction_id", "factions", "fk_relationships_target_faction_id_factions"),
    ("colour", None, None),
    ("mirror_relationship_id", "relationships", "fk_relationships_mirror_relationship_id_relationships"),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("relationships"):
        return
    present = {column["name"] for column in inspector.get_columns("relationships")}
    missing = [entry for entry in COLUMNS if entry[0] not in present]
    if not missing:
        return
    with op.batch_alter_table("relationships") as batch:
        for name, target, constraint in missing:
            batch.add_column(sa.Column(name, sa.String(), nullable=True))
            if target is not None:
                batch.create_foreign_key(constraint, target, [name], ["id"])
    if "faction_id" in {entry[0] for entry in missing}:
        op.create_index("ix_relationships_faction_id", "relationships", ["faction_id"])
        op.create_index("ix_relationships_target_faction_id", "relationships", ["target_faction_id"])


def downgrade() -> None:
    op.drop_index("ix_relationships_target_faction_id", table_name="relationships")
    op.drop_index("ix_relationships_faction_id", table_name="relationships")
    with op.batch_alter_table("relationships") as batch:
        for name, target, constraint in reversed(COLUMNS):
            if target is not None:
                batch.drop_constraint(constraint, type_="foreignkey")
            batch.drop_column(name)
