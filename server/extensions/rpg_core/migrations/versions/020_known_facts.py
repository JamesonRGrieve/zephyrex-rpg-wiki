# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 020: what a player's character has learned (operator, 2026-11-24: "only player visible
information and learned facts should be present there").

``known_facts``: one person's knowledge of one record, as text, or with none, that they know of it,
and the session report it was learned in. Inspector-guarded."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020_rpg_core_known_facts"
down_revision: Union[str, None] = "019_rpg_core_reality"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "rpg_core"}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "known_facts" not in set(inspector.get_table_names()):
        op.create_table(
            "known_facts",
            sa.Column("person_id", sa.String(), sa.ForeignKey("persons.id"), nullable=True, comment="Optional foreign key to PersonModel"),
            sa.Column("target_entity_type", sa.String(), nullable=True, comment="The record's type: contract/wiki.json entity_types"),
            sa.Column("target_entity_id", sa.String(), nullable=True, comment="The record learned about"),
            sa.Column("text", sa.String(), nullable=True, comment="What they learned; none: they know of it"),
            sa.Column("learned_in_journal_id", sa.String(), sa.ForeignKey("journals.id"), nullable=True, comment="The session it was learned in"),
            sa.Column("campaign_id", sa.String(), sa.ForeignKey("campaigns.id"), nullable=True, comment="The person's campaign (set from the person)"),
            sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_by_user_id", sa.String(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            comment="What a person has learned about a record, or that they know of it.",
            info=TABLE_INFO,
        )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("known_facts")}
    if "ix_known_facts_person_id" not in indexes:
        op.create_index("ix_known_facts_person_id", "known_facts", ["person_id"])
    if "ix_known_facts_target_entity_id" not in indexes:
        op.create_index("ix_known_facts_target_entity_id", "known_facts", ["target_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_known_facts_target_entity_id", table_name="known_facts")
    op.drop_index("ix_known_facts_person_id", table_name="known_facts")
    op.drop_table("known_facts")
