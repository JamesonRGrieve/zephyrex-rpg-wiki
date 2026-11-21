# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 004: campaign_id on world_taxonomy's ``taxons`` and ``statuses``, with real foreign keys,
as 001–003 do for the other world tables. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_rpg_core_taxonomy"
down_revision: Union[str, None] = "003_rpg_core_hooks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("taxons", "statuses")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in TABLES:
        if not inspector.has_table(table) or "campaign_id" in {column["name"] for column in inspector.get_columns(table)}:
            continue
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("campaign_id", sa.String(), nullable=True, comment="Optional foreign key to CampaignModel"))
            batch.create_foreign_key(f"fk_{table}_campaign_id_campaigns", "campaigns", ["campaign_id"], ["id"])


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"fk_{table}_campaign_id_campaigns", type_="foreignkey")
            batch.drop_column("campaign_id")
