# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 011: the shared play-style tags (operator, 2026-11-21: "tag scenarios as freeform, combat
heavy, narrative, mystery, etc."). The contract's seed_play_styles are written as taxons of kind
play_style, setting- and campaign-free, as the framework's SYSTEM user: readable by everyone,
changeable only by ROOT and SYSTEM, like the seeded settings (006). A name already held by SYSTEM is
left as it is, so this is safe on any database. People add their own beside them. The downgrade
removes only the seeded rows nobody has changed (updated_at unset).
"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from zephyrex.extensions.wiki_shared.Contract import PLAY_STYLE, SEED_PLAY_STYLES  # type: ignore[import-not-found]
from zephyrex.lib.Environment import env

revision: str = "011_rpg_core_play_styles"
down_revision: Union[str, None] = "010_rpg_core_provenance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

taxons = sa.table(
    "taxons",
    sa.column("id", sa.String),
    sa.column("name", sa.String),
    sa.column("kind", sa.String),
    sa.column("created_by_user_id", sa.String),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    bind = op.get_bind()
    if "taxons" not in set(sa.inspect(bind).get_table_names()):
        return
    held = {
        row.name
        for row in bind.execute(
            sa.select(taxons.c.name).where(taxons.c.kind == PLAY_STYLE, taxons.c.created_by_user_id == env("SYSTEM_ID"))
        ).all()
    }
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seeded = [
        {"id": str(uuid.uuid4()), "name": name, "kind": PLAY_STYLE, "created_by_user_id": env("SYSTEM_ID"), "created_at": now}
        for name in SEED_PLAY_STYLES
        if name not in held
    ]
    if seeded:
        op.bulk_insert(taxons, seeded)


def downgrade() -> None:
    op.execute(
        taxons.delete().where(
            taxons.c.kind == PLAY_STYLE,
            taxons.c.name.in_(list(SEED_PLAY_STYLES)),
            taxons.c.created_by_user_id == env("SYSTEM_ID"),
            taxons.c.updated_at.is_(None),
        )
    )
