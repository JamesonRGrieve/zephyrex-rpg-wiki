# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_spatial extension definition. Depends on nothing of this repo's: Tier 1 stays
campaign-free, and rpg_core points at it, never the other way (operator, 2026-11-20)."""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class WorldSpatialExtension(AbstractStaticExtension):
    name: ClassVar[str] = "world_spatial"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "Locations as a tree, at every scale from a star system to a room"
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(
                name="acl_rbac",
                friendly_name="ACL / RBAC",
                optional=True,
                reason="Per-row visibility for secret places",
            ),
        ]
    )
