# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_inventory extension (OBJECT_PLAN Tier 1): the item catalogue, the items themselves (where
each is, whose it is), and what any entity carries (W8). Depends on genealogy and world_spatial only,
as OBJECT_PLAN §3 lists. What a faction holds is an EntityInventory row (target_entity_type
"faction"), not an owner_faction_id on the item: that column would need world_social, an edge
OBJECT_PLAN doesn't list (Zephyrex RPG, 2026-11-20; it differs from zephyrex-vtt's rpg_state here)."""
