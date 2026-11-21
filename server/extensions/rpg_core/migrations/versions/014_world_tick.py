# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 014: the world tick (operator, 2026-11-21: "each character should have its own routine and
motivations and the GM/decision agent should pilot them on the map as time advances").

``persons.routine`` and ``persons.motivations`` (JSON text), ``campaigns.clock_minutes`` (in-world
minutes from day 1, 00:00), and ``person_moves``: each move the GM side makes, from where, to where,
when in-world and why. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_rpg_core_world_tick"
down_revision: Union[str, None] = "013_rpg_core_scenarios"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "rpg_core"}


def _columns(inspector: sa.engine.reflection.Inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "persons" in tables:
        present = _columns(inspector, "persons")
        with op.batch_alter_table("persons") as batch:
            if "routine" not in present:
                batch.add_column(sa.Column("routine", sa.String(), nullable=True, comment="Their schedule, as JSON text (GM-facing)"))
            if "motivations" not in present:
                batch.add_column(sa.Column("motivations", sa.String(), nullable=True, comment="Their goals, fears and intent, as JSON text (GM-facing)"))
    if "campaigns" in tables and "clock_minutes" not in _columns(inspector, "campaigns"):
        with op.batch_alter_table("campaigns") as batch:
            batch.add_column(sa.Column("clock_minutes", sa.Integer(), nullable=True, comment="In-world minutes from day 1, 00:00"))
    if "person_moves" not in tables:
        op.create_table(
            "person_moves",
            sa.Column("person_id", sa.String(), sa.ForeignKey("persons.id"), nullable=True, comment="Optional foreign key to PersonModel"),
            sa.Column("campaign_id", sa.String(), sa.ForeignKey("campaigns.id"), nullable=True, comment="The campaign whose clock dated it"),
            sa.Column("from_location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=True, comment="Where they were"),
            sa.Column("to_location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=True, comment="Where they went"),
            sa.Column("at_minutes", sa.Integer(), nullable=True, comment="The campaign's clock when they moved"),
            sa.Column("reason", sa.String(), nullable=True, comment="Why they moved"),
            sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_by_user_id", sa.String(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            comment="A person moved by the GM: from where, to where, when in-world and why.",
            info=TABLE_INFO,
        )


def downgrade() -> None:
    op.drop_table("person_moves")
    with op.batch_alter_table("campaigns") as batch:
        batch.drop_column("clock_minutes")
    with op.batch_alter_table("persons") as batch:
        batch.drop_column("motivations")
        batch.drop_column("routine")
