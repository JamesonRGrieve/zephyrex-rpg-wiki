# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 013: copy on start (operator, 2026-11-21). ``campaigns.is_scenario`` marks a scenario,
which play never edits, and ``campaigns.scenario_id`` names the scenario a playthrough was copied
from, a real foreign key. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_rpg_core_scenarios"
down_revision: Union[str, None] = "012_rpg_core_picture_urls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "campaigns" not in set(inspector.get_table_names()):
        return
    present = {column["name"] for column in inspector.get_columns("campaigns")}
    with op.batch_alter_table("campaigns") as batch:
        if "is_scenario" not in present:
            batch.add_column(sa.Column("is_scenario", sa.Boolean(), nullable=True, comment="A scenario: play never edits it; starting it copies it"))
        if "scenario_id" not in present:
            batch.add_column(sa.Column("scenario_id", sa.String(), nullable=True, comment="The scenario this campaign is a playthrough of"))
            batch.create_foreign_key("fk_campaigns_scenario_id_campaigns", "campaigns", ["scenario_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("campaigns") as batch:
        batch.drop_constraint("fk_campaigns_scenario_id_campaigns", type_="foreignkey")
        batch.drop_column("scenario_id")
        batch.drop_column("is_scenario")
