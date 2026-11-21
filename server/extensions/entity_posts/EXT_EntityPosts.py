# SPDX-License-Identifier: AGPL-3.0-or-later
"""entity_posts extension definition: Tier 0, depends on nothing of this repo's (its target is
polymorphic: target_entity_type + target_entity_id)."""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class EntityPostsExtension(AbstractStaticExtension):
    name: ClassVar[str] = "entity_posts"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "Pinnable rich-text posts on any entity"
    dependencies: ClassVar[Dependencies] = Dependencies(
        [EXT_Dependency(name="acl_rbac", friendly_name="ACL / RBAC", optional=True, reason="Per-post visibility (W9)")]
    )
