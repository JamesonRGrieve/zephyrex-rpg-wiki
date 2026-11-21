# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_taxonomy extension definition (W6). Tier 1, campaign-free; rpg_core points at it, never
back. Its links to records are polymorphic, so it depends on no other world extension."""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class WorldTaxonomyExtension(AbstractStaticExtension):
    name: ClassVar[str] = "world_taxonomy"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "Tags, categories, races and other classifications, and statuses"
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(name="acl_rbac", friendly_name="ACL / RBAC", optional=True, reason="Per-row visibility for secret tags"),
        ]
    )
