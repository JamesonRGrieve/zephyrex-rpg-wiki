"""rpg_log extension definition.

Owns event-log tables. Depends on rpg_state for character / location /
item / trait / campaign references.
"""

from typing import ClassVar

from zephyrex.extensions.AbstractExtensionProvider import (
    AbstractStaticExtension,
)
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class RPGLogExtension(AbstractStaticExtension):
    name: ClassVar[str] = "rpg_log"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Event-log schema for RPG campaigns (combat, dialogue, transactions)"
    )
    dependencies: ClassVar[Dependencies] = Dependencies(
        [
            EXT_Dependency(
                name="rpg_state",
                friendly_name="RPG State",
                optional=False,
                reason="Character, location, item, trait and campaign references",
            ),
        ]
    )
