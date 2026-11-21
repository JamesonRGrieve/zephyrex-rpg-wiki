# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 015: a scenario started in the background (operator, 2026-11-21: "make it async with the
progress bar and auto load it when it's done").

``campaign_starts``: each start's scenario, its playthrough once made, its state (running, done,
failed), its progress through the steps, and when done its id map, when failed why. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_rpg_core_campaign_starts"
down_revision: Union[str, None] = "014_rpg_core_world_tick"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "rpg_core"}


def upgrade() -> None:
    if "campaign_starts" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "campaign_starts",
        sa.Column("scenario_id", sa.String(), nullable=True, comment="The scenario being started"),
        sa.Column("campaign_id", sa.String(), nullable=True, comment="The playthrough, once made"),
        sa.Column("name", sa.String(), nullable=True, comment="The playthrough's name as asked for"),
        sa.Column("state", sa.String(), nullable=True, comment="running, done or failed"),
        sa.Column("done", sa.Integer(), nullable=True, comment="Steps finished"),
        sa.Column("total", sa.Integer(), nullable=True, comment="Steps in all"),
        sa.Column("step", sa.String(), nullable=True, comment="The step under way"),
        sa.Column("id_map", sa.String(), nullable=True, comment="When done: each copied id → its copy's, as JSON text"),
        sa.Column("error", sa.String(), nullable=True, comment="When failed: why"),
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
        sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by_user_id", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="A scenario being started in the background: state, progress, and the playthrough.",
        info=TABLE_INFO,
    )


def downgrade() -> None:
    op.drop_table("campaign_starts")
