# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core extension (OBJECT_PLAN Tier 2): campaigns (a campaign is a world in the
wiki's screens), and the campaign scoping of the world_* records. It widens genealogy's Person into
the character table and gives Location its campaign, by @extension_model, so dependencies point one
way only: rpg_core → world_* (operator, 2026-11-20). Game systems are zephyrex-vtt's rpg_systems (operator,
2026-11-20). Ported from zephyrex-vtt's rpg_state
(OBJECT_PLAN §6) with the same table and field names."""
