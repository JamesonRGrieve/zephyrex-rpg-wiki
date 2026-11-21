# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_narrative 002: the plot-hook DAG (``hooks``, ``hook_dependencies``, ``person_hooks``,
``faction_hooks``), moved from vtt's rpg_state (OBJECT_PLAN §6). A database whose tables came from
rpg_state's create_all keeps its rows: an existing table gains only the columns it lacks (``entry``,
``giver_person_id`` on hooks). hooks.campaign_id is rpg_core's (rpg_core's 003 adds it).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_world_narrative_hooks"
down_revision: Union[str, None] = "001_world_narrative_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "world_narrative"}


def _inspector() -> sa.engine.reflection.Inspector:
    return sa.inspect(op.get_bind())


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


def _progress_columns() -> list:
    return [
        sa.Column("status", sa.String(), nullable=True, comment="Free-form, at most 40 characters"),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("progress", sa.Float(), nullable=True, comment="For incremental hooks"),
    ]


def _hook_ref(name: str) -> sa.Column:
    return sa.Column(name, sa.String(), sa.ForeignKey("hooks.id", ondelete="CASCADE"), nullable=True, comment="Foreign key to HookModel")


def _add_missing(table: str, columns: list[sa.Column]) -> None:
    present = {column["name"] for column in _inspector().get_columns(table)}
    missing = [column for column in columns if column.name not in present]
    if missing:
        with op.batch_alter_table(table) as batch:
            for column in missing:
                batch.add_column(column)


def upgrade() -> None:
    tables = set(_inspector().get_table_names())
    if "hooks" not in tables:
        op.create_table(
            "hooks",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("kind", sa.String(), nullable=True, comment="contract/wiki.json hook_kinds"),
            sa.Column("entry", sa.String(), nullable=True, comment="The entry: a Plate value as JSON text"),
            sa.Column("giver_person_id", sa.String(), sa.ForeignKey("persons.id"), nullable=True, comment="Optional foreign key to PersonModel"),
            sa.Column("giver_faction_id", sa.String(), sa.ForeignKey("factions.id"), nullable=True, comment="Optional foreign key to FactionModel"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A plot hook: quest, objective, thread, mystery, rumour, obligation, foreshadowing, hint or background.",
            info=TABLE_INFO,
        )
        op.create_index("ix_hooks_deleted_at", "hooks", ["deleted_at"])
    else:
        # rpg_state's create_all table: no entry and no giver_person_id yet.
        _add_missing(
            "hooks",
            [
                sa.Column("entry", sa.String(), nullable=True, comment="The entry: a Plate value as JSON text"),
                sa.Column("giver_person_id", sa.String(), sa.ForeignKey("persons.id", name="fk_hooks_giver_person_id_persons"), nullable=True),
            ],
        )
    if "hook_dependencies" not in tables:
        op.create_table(
            "hook_dependencies",
            _hook_ref("parent_hook_id"),
            _hook_ref("child_hook_id"),
            sa.Column("reason", sa.String(), nullable=True),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("parent_hook_id", "child_hook_id", name="uq_hook_dependencies_edge"),
            comment="An edge of the hook DAG: the child hook waits on the parent. No cycles.",
            info=TABLE_INFO,
        )
    for table, actor, target in (("person_hooks", "person_id", "persons"), ("faction_hooks", "faction_id", "factions")):
        if table not in tables:
            op.create_table(
                table,
                sa.Column(actor, sa.String(), sa.ForeignKey(f"{target}.id", ondelete="CASCADE"), nullable=True),
                _hook_ref("hook_id"),
                *_progress_columns(),
                *_audit_columns(),
                sa.PrimaryKeyConstraint("id"),
                sa.UniqueConstraint(actor, "hook_id", name=f"uq_{table}_{actor}_hook_id"),
                comment=f"Progress on a hook; one per {actor[:-3]} and hook.",
                info=TABLE_INFO,
            )


def downgrade() -> None:
    for table in ("faction_hooks", "person_hooks", "hook_dependencies"):
        op.drop_table(table)
    op.drop_index("ix_hooks_deleted_at", table_name="hooks")
    op.drop_table("hooks")
