# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core 006: setting slugs and the seeded settings (S6b).

``settings.slug``: a setting's stable name (contract/wiki.json setting_slug), unique. Settings made
before this get their name's slug, numbered past any taken, oldest first. Then the contract's
seed_settings are written as the framework's SYSTEM user (readable by everyone, changeable only by
ROOT and SYSTEM); a slug already held is left as it is, so this is safe on any database. vtt's game
systems name these settings by slug. Inspector-guarded: a present column or index is kept. The
downgrade removes only the seeded rows nobody has changed since (their updated_at is unset).
"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from zephyrex.extensions.wiki_shared.Contract import SEED_SETTINGS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import free_slug, slugify  # type: ignore[import-not-found]
from zephyrex.lib.Environment import env

revision: str = "006_rpg_core_setting_slugs"
down_revision: Union[str, None] = "005_rpg_core_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX = "ix_settings_slug"

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
    inspector = sa.inspect(bind)
    if "slug" not in {column["name"] for column in inspector.get_columns("settings")}:
        with op.batch_alter_table("settings") as batch:
            batch.add_column(
                sa.Column("slug", sa.String(), nullable=True, comment="Its stable name: unique, fixed once set")
            )
    rows = bind.execute(
        sa.select(settings.c.id, settings.c.name, settings.c.slug).order_by(settings.c.created_at, settings.c.id)
    ).all()
    taken = {row.slug for row in rows if row.slug}
    for row in rows:
        if row.slug:
            continue
        slug = free_slug(slugify(row.name or ""), taken)
        taken.add(slug)
        bind.execute(settings.update().where(settings.c.id == row.id).values(slug=slug))
    if INDEX not in {index["name"] for index in sa.inspect(bind).get_indexes("settings")}:
        op.create_index(INDEX, "settings", ["slug"], unique=True)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seeded = [
        {
            "id": str(uuid.uuid4()),
            "name": one["name"],
            "slug": one["slug"],
            "created_by_user_id": env("SYSTEM_ID"),
            "created_at": now,
        }
        for one in SEED_SETTINGS
        if one["slug"] not in taken
    ]
    if seeded:
        op.bulk_insert(settings, seeded)


def downgrade() -> None:
    slugs = [one["slug"] for one in SEED_SETTINGS]
    op.execute(
        settings.delete().where(
            settings.c.slug.in_(slugs),
            settings.c.created_by_user_id == env("SYSTEM_ID"),
            settings.c.updated_at.is_(None),
        )
    )
    op.drop_index(INDEX, table_name="settings")
    with op.batch_alter_table("settings") as batch:
        batch.drop_column("slug")
