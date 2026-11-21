# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_narrative 003: narrative state, from dh-campaign's tracker (W56, W57). ``hooks`` gain a
requirement expression, an excuse and their resolution (when, and the session report it happened
in); new ``dispositions`` (how a person regards the party, a person or an organisation, and the
hook that changes it) and ``relation_influences`` (a hook that changes a relation's attitude).
Inspector-guarded: present columns and tables are kept.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_world_narrative_state"
down_revision: Union[str, None] = "002_world_narrative_hooks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "world_narrative"}
HOOK_COLUMNS = (
    ("requires", sa.String(), None),
    ("excuse", sa.String(), None),
    ("resolved_at", sa.DateTime(), None),
    ("resolved_journal_id", sa.String(), ("journals", "fk_hooks_resolved_journal_id_journals")),
)


def _audit_columns() -> list:
    return [
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
        sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, comment="Optional foreign key to UserModel"),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by_user_id", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    ]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "hooks" in tables:
        present = {column["name"] for column in inspector.get_columns("hooks")}
        missing = [entry for entry in HOOK_COLUMNS if entry[0] not in present]
        if missing:
            with op.batch_alter_table("hooks") as batch:
                for name, kind, foreign in missing:
                    batch.add_column(sa.Column(name, kind, nullable=True))
                    if foreign is not None:
                        batch.create_foreign_key(foreign[1], foreign[0], [name], ["id"])
    if "dispositions" not in tables:
        op.create_table(
            "dispositions",
            sa.Column("person_id", sa.String(), sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=True, comment="Whose attitude"),
            sa.Column("target_kind", sa.String(), nullable=True, comment="party, person or faction"),
            sa.Column("target_person_id", sa.String(), sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=True),
            sa.Column("target_faction_id", sa.String(), sa.ForeignKey("factions.id", ondelete="CASCADE"), nullable=True),
            sa.Column("attitude", sa.String(), nullable=True, comment="contract/wiki.json attitudes, or a nuance of one"),
            sa.Column("is_default", sa.Boolean(), nullable=True),
            sa.Column("trigger_hook_id", sa.String(), sa.ForeignKey("hooks.id", ondelete="CASCADE"), nullable=True),
            sa.Column("note", sa.String(), nullable=True),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="How a person regards the party, a person or an organisation, and what changes it.",
            info=TABLE_INFO,
        )
        op.create_index("ix_dispositions_person_id", "dispositions", ["person_id"])
    if "relation_influences" not in tables:
        op.create_table(
            "relation_influences",
            sa.Column("relationship_id", sa.String(), sa.ForeignKey("relationships.id", ondelete="CASCADE"), nullable=True),
            sa.Column("hook_id", sa.String(), sa.ForeignKey("hooks.id", ondelete="CASCADE"), nullable=True),
            sa.Column("to_intensity", sa.Float(), nullable=True, comment="The relation's attitude once the hook resolves"),
            sa.Column("note", sa.String(), nullable=True),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A hook that changes a relation's attitude when it resolves.",
            info=TABLE_INFO,
        )


def downgrade() -> None:
    op.drop_table("relation_influences")
    op.drop_index("ix_dispositions_person_id", table_name="dispositions")
    op.drop_table("dispositions")
    with op.batch_alter_table("hooks") as batch:
        batch.drop_constraint("fk_hooks_resolved_journal_id_journals", type_="foreignkey")
        for name, _kind, _foreign in reversed(HOOK_COLUMNS):
            batch.drop_column(name)
