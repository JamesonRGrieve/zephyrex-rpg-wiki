# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core extension definition: depends on genealogy (Person) and world_spatial (Location), and
nothing depends back on it from Tier 1 (operator, 2026-11-20)."""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class RPGCoreExtension(AbstractStaticExtension):
    name: ClassVar[str] = "rpg_core"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Game systems and campaigns; widens Person into the character table and scopes world records to a campaign"
    )
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(
                name="genealogy",
                friendly_name="Genealogy",
                optional=False,
                reason="rpg_core widens genealogy's Person into the character table",
            ),
            EXT_Dependency(
                name="world_spatial",
                friendly_name="World: places",
                optional=False,
                reason="rpg_core scopes locations to a campaign, and a person stands in a location",
            ),
            EXT_Dependency(
                name="acl_rbac",
                friendly_name="ACL / RBAC",
                optional=True,
                reason="Per-row visibility for GM-secret records",
            ),
        ]
    )
