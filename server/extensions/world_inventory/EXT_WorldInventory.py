# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_inventory extension definition: depends on genealogy and world_spatial (OBJECT_PLAN §3)."""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class WorldInventoryExtension(AbstractStaticExtension):
    name: ClassVar[str] = "world_inventory"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "Item catalogue, items, and what any entity carries"
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(
                name="genealogy",
                friendly_name="Genealogy",
                optional=False,
                reason="An item's owner is a person",
            ),
            EXT_Dependency(
                name="world_spatial",
                friendly_name="World: places",
                optional=False,
                reason="An item sits in a place",
            ),
            EXT_Dependency(
                name="acl_rbac",
                friendly_name="ACL / RBAC",
                optional=True,
                reason="Per-row visibility for hidden treasure",
            ),
        ]
    )
