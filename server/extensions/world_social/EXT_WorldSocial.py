# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_social extension definition. Tier 1, campaign-free; rpg_core points at it, never back.
Depends on genealogy, whose relationships it widens with organisation endpoints (W5)."""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class WorldSocialExtension(AbstractStaticExtension):
    name: ClassVar[str] = "world_social"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "Organisations and families as a tree, and relations between people and organisations"
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(name="genealogy", friendly_name="Genealogy", optional=False, reason="Relations widen genealogy's relationships"),
            EXT_Dependency(
                name="acl_rbac",
                friendly_name="ACL / RBAC",
                optional=True,
                reason="Per-row visibility for secret societies",
            ),
        ]
    )
