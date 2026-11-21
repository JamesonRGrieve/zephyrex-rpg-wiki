# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 003: campaign_id on world_narrative's ``hooks``, with its real foreign key, as 001 and 002 do
for the other world tables. Hooks are left out of world_entities (GM secrets until W9). Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_rpg_core_hooks"
down_revision: Union[str, None] = "002_rpg_core_journals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("hooks"):
        return
    if "campaign_id" in {column["name"] for column in inspector.get_columns("hooks")}:
        return
    with op.batch_alter_table("hooks") as batch:
        batch.add_column(sa.Column("campaign_id", sa.String(), nullable=True, comment="Optional foreign key to CampaignModel"))
        batch.create_foreign_key("fk_hooks_campaign_id_campaigns", "campaigns", ["campaign_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("hooks") as batch:
        batch.drop_constraint("fk_hooks_campaign_id_campaigns", type_="foreignkey")
        batch.drop_column("campaign_id")
