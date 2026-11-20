# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial migration for world_inventory: owns ``items``, ``item_instances`` and
``entity_inventories``. After world_spatial (an item sits in a place) and genealogy (its owner is a
person). Items' campaign_id is rpg_core's (rpg_core's 001 adds it); game_system_id is
zephyrex-vtt's rpg_systems'.
Inspector-guarded, like the framework's 001s.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_world_inventory_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("ext_world_inventory",)
# No depends_on: each extension has its own Alembic history, so another extension's revision can't
# be named. The framework orders extensions by their required EXT_Dependency and their FKs
# (world_inventory → genealogy, world_spatial; EXT_WorldInventory.py).
depends_on: Union[str, Sequence[str], None] = None

TABLE_INFO = {"extension": "world_inventory"}


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


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
    if not _has_table("items"):
        op.create_table(
            "items",
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("kind", sa.String(), nullable=True, comment="contract/wiki.json item_kinds"),
            sa.Column("entry", sa.String(), nullable=True, comment="The entry: a Plate value as JSON text"),
            sa.Column("weight", sa.Float(), nullable=True, comment="Per-unit weight"),
            sa.Column("base_value", sa.Float(), nullable=True, comment="Default value per unit"),
            sa.Column("stack_size", sa.Integer(), nullable=True, comment="Most units per stack"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="A kind of thing (the catalogue).",
            info=TABLE_INFO,
        )
        op.create_index("ix_items_deleted_at", "items", ["deleted_at"])
    if not _has_table("item_instances"):
        op.create_table(
            "item_instances",
            sa.Column("item_id", sa.String(), sa.ForeignKey("items.id"), nullable=True, comment="Optional foreign key to ItemModel"),
            sa.Column("location_id", sa.String(), sa.ForeignKey("locations.id"), nullable=True, comment="Optional foreign key to LocationModel"),
            sa.Column("owner_person_id", sa.String(), sa.ForeignKey("persons.id"), nullable=True, comment="Optional foreign key to PersonModel"),
            sa.Column("quantity", sa.Integer(), nullable=True, comment="How many (>=1)"),
            sa.Column("durability", sa.Float(), nullable=True, comment="System-defined durability"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="One item in the world: where it is and whose it is.",
            info=TABLE_INFO,
        )
        op.create_index("ix_item_instances_deleted_at", "item_instances", ["deleted_at"])
    if not _has_table("entity_inventories"):
        op.create_table(
            "entity_inventories",
            sa.Column("item_instance_id", sa.String(), sa.ForeignKey("item_instances.id"), nullable=True, comment="Optional foreign key to ItemInstanceModel"),
            sa.Column("target_entity_type", sa.String(), nullable=True, comment="contract/wiki.json entity_types"),
            sa.Column("target_entity_id", sa.String(), nullable=True, comment="The carrier's id, in its own table"),
            sa.Column("quantity", sa.Integer(), nullable=True, comment="How many it carries (>=1)"),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id"),
            comment="What an entity carries now (W8). Polymorphic target, so no FK on it.",
            info=TABLE_INFO,
        )
        op.create_index("ix_entity_inventories_deleted_at", "entity_inventories", ["deleted_at"])
        op.create_index("ix_entity_inventories_target", "entity_inventories", ["target_entity_type", "target_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_entity_inventories_target", table_name="entity_inventories")
    op.drop_index("ix_entity_inventories_deleted_at", table_name="entity_inventories")
    op.drop_table("entity_inventories")
    op.drop_index("ix_item_instances_deleted_at", table_name="item_instances")
    op.drop_table("item_instances")
    op.drop_index("ix_items_deleted_at", table_name="items")
    op.drop_table("items")
