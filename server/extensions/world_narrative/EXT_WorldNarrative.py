# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_narrative extension definition: depends on genealogy (authors) and world_spatial (places)."""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class WorldNarrativeExtension(AbstractStaticExtension):
    name: ClassVar[str] = "world_narrative"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "Journals: session reports, diaries, lore, handouts, notes and manuscripts"
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(name="genealogy", friendly_name="Genealogy", optional=False, reason="A journal's author is a person"),
            EXT_Dependency(name="world_spatial", friendly_name="World: places", optional=False, reason="A journal can be set in a place"),
            EXT_Dependency(name="acl_rbac", friendly_name="ACL / RBAC", optional=True, reason="Per-row visibility for secret lore"),
        ]
    )
