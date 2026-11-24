# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 021: where a campaign is kept (the operator, 2026-11-24, "Framework selector": a
Foundry-backed campaign).

``campaigns.backend`` (contract/wiki.json campaign_backends: native, the default when none, or
foundry) and ``campaigns.foundry_world_id`` (the Foundry world's provider instance). rpg_core's
backend selector reads them. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021_rpg_core_campaign_backends"
down_revision: Union[str, None] = "020_rpg_core_known_facts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    present = {column["name"] for column in inspector.get_columns("campaigns")}
    with op.batch_alter_table("campaigns") as batch:
        if "backend" not in present:
            batch.add_column(sa.Column("backend", sa.String(), nullable=True, comment="Where it is kept: native (none) or foundry"))
        if "foundry_world_id" not in present:
            batch.add_column(
                sa.Column(
                    "foundry_world_id",
                    sa.String(),
                    sa.ForeignKey("provider_instances.id", name="fk_campaigns_foundry_world_id"),
                    nullable=True,
                    comment="The Foundry world a foundry campaign is kept in",
                )
            )


def downgrade() -> None:
    with op.batch_alter_table("campaigns") as batch:
        batch.drop_column("foundry_world_id")
        batch.drop_column("backend")
