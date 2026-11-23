# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 019: Reality replaces Modern (operator, 2026-11-23).

Reality is one setting with eras inside it: the seeded "modern" row is renamed in place
("reality", "Reality"), keeping its id, so every campaign and canon record on it stays attached;
with neither, Reality is made as SYSTEM's. No row is ever removed."""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from zephyrex.lib.Environment import env

revision: str = "019_rpg_core_reality"
down_revision: Union[str, None] = "018_rpg_core_tts_voice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

settings = sa.table(
    "settings",
    sa.column("id", sa.String),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("created_by_user_id", sa.String),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    bind = op.get_bind()
    held = {row.slug: row for row in bind.execute(sa.select(settings.c.id, settings.c.slug, settings.c.created_by_user_id).where(settings.c.slug.in_(["modern", "reality"]))).all()}
    if "reality" in held:
        return
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    modern = held.get("modern")
    if modern is not None and modern.created_by_user_id == env("SYSTEM_ID"):
        bind.execute(settings.update().where(settings.c.id == modern.id).values(slug="reality", name="Reality", updated_at=now))
        return
    op.bulk_insert(settings, [{"id": str(uuid.uuid4()), "name": "Reality", "slug": "reality", "created_by_user_id": env("SYSTEM_ID"), "created_at": now}])


def downgrade() -> None:
    # Reality stays: it may hold campaigns and canon by now, and Modern was its old name only.
    pass
