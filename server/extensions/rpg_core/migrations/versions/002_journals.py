# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 002: campaign_id on world_narrative's ``journals``, with its real foreign key, as 001 does
for the other world tables. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_rpg_core_journals"
down_revision: Union[str, None] = "001_rpg_core_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("journals"):
        return
    if "campaign_id" in {column["name"] for column in inspector.get_columns("journals")}:
        return
    with op.batch_alter_table("journals") as batch:
        batch.add_column(sa.Column("campaign_id", sa.String(), nullable=True, comment="Optional foreign key to CampaignModel"))
        batch.create_foreign_key("fk_journals_campaign_id_campaigns", "campaigns", ["campaign_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("journals") as batch:
        batch.drop_constraint("fk_journals_campaign_id_campaigns", type_="foreignkey")
        batch.drop_column("campaign_id")
