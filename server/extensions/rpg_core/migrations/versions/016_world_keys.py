# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 016: the world's activation index (operator, 2026-11-22: "Why is it reading the whole
world instead of tag/relevance based injection?").

``world_keys``: each record's activation keys (its name, aliases and keywords, normalised; "*" when
always active), indexed by key, so world_entities_matching looks a turn's words up instead of reading
a setting. Records made before this are indexed by the rebuild_world_keys ability; hooks keep the
index current after. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_rpg_core_world_keys"
down_revision: Union[str, None] = "015_rpg_core_campaign_starts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "rpg_core"}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "world_keys" not in set(inspector.get_table_names()):
        op.create_table(
            "world_keys",
            sa.Column("key", sa.String(), nullable=True, comment="Normalised: accents dropped, case folded, words single-spaced"),
            sa.Column("target_entity_type", sa.String(), nullable=True, comment="The record's type"),
            sa.Column("target_entity_id", sa.String(), nullable=True, comment="The record"),
            sa.Column("campaign_id", sa.String(), nullable=True, comment="The record's campaign; none for a setting's canon"),
            sa.Column("setting_id", sa.String(), nullable=True, comment="The record's setting, for its canon"),
            sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_by_user_id", sa.String(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            comment="A record's activation key, for the narrator's relevance read (world_entities_matching).",
            info=TABLE_INFO,
        )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("world_keys")}
    if "ix_world_keys_key" not in indexes:
        op.create_index("ix_world_keys_key", "world_keys", ["key"])
    if "ix_world_keys_target_entity_id" not in indexes:
        op.create_index("ix_world_keys_target_entity_id", "world_keys", ["target_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_world_keys_target_entity_id", table_name="world_keys")
    op.drop_index("ix_world_keys_key", table_name="world_keys")
    op.drop_table("world_keys")
