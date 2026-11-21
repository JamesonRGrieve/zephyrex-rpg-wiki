# SPDX-License-Identifier: AGPL-3.0-or-later
"""world_properties extension definition (W4). Tier 1, campaign-free; rpg_core points at it, never
back. A record's properties are the framework's record_metadata, which a kit's apply writes."""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class WorldPropertiesExtension(AbstractStaticExtension):
    name: ClassVar[str] = "world_properties"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "Property kits: keys with types and defaults, applied to any record's properties"
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(
                name="metadata",
                friendly_name="Metadata",
                optional=False,
                reason="A record's properties are the framework's record_metadata, which applying a kit writes",
            ),
        ]
    )
