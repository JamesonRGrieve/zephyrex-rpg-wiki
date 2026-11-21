# SPDX-License-Identifier: AGPL-3.0-or-later
"""rpg_core extension definition: depends on genealogy (Person) and world_spatial (Location), and
nothing depends back on it from Tier 1 (operator, 2026-11-20)."""

from datetime import datetime
from typing import Any, ClassVar, Optional

from zephyrex.extensions.AbstractExtensionProvider import AbstractStaticExtension, ability
from zephyrex.lib.Dependencies import Dependencies, EXT_Dependency


class RPGCoreExtension(AbstractStaticExtension):
    name: ClassVar[str] = "rpg_core"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Campaigns; widens Person into the character table and scopes world records to a campaign"
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
                name="world_social",
                friendly_name="World: organisations",
                optional=False,
                reason="rpg_core scopes factions to a campaign",
            ),
            EXT_Dependency(
                name="world_inventory",
                friendly_name="World: items",
                optional=False,
                reason="rpg_core scopes items to a campaign",
            ),
            EXT_Dependency(
                name="world_narrative",
                friendly_name="World: journals",
                optional=False,
                reason="rpg_core scopes journals to a campaign and writes session reports",
            ),
            EXT_Dependency(
                name="acl_rbac",
                friendly_name="ACL / RBAC",
                optional=True,
                reason="Per-row visibility for GM-secret records",
            ),
        ]
    )

    # rpg-ai A24 calls these through loaded_ability(model_registry, "rpg_core", name). The caller
    # passes the registry and whose permissions they act with (the campaign's GM).

    @classmethod
    @ability("session_report")
    def session_report(
        cls,
        model_registry: Any,
        requester_id: str,
        campaign_id: str,
        title: str,
        body: str | list[Any],
        occurred_at: Optional[datetime] = None,
        session_number: Optional[int] = None,
        mentions: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, str]:
        """Write a session report into the campaign as a journal; ``{"id": ...}``."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import (  # type: ignore[import-not-found]
            SessionReportIn,
            write_session_report,
        )

        report = SessionReportIn(
            campaign_id=campaign_id,
            title=title,
            body=body,
            occurred_at=occurred_at,
            session_number=session_number,
            mentions=mentions or [],
        )
        return {"id": write_session_report(model_registry, requester_id, report)}

    @classmethod
    @ability("session_report_get")
    def session_report_get(cls, model_registry: Any, requester_id: str, report_id: str) -> dict[str, Any]:
        """A session report as its review sheet reads it."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import read_session_report  # type: ignore[import-not-found]

        return read_session_report(model_registry, requester_id, report_id).model_dump(mode="json")

    @classmethod
    @ability("world_entities")
    def world_entities(
        cls,
        model_registry: Any,
        requester_id: str,
        campaign_id: str,
        since: Optional[datetime] = None,
        kinds: Optional[list[str]] = None,
        after: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """A campaign's changed entities since a time, tombstones included (rpg-ai A15)."""
        from zephyrex.extensions.rpg_core.BLL_RPGCore import world_entities  # type: ignore[import-not-found]

        return world_entities(model_registry, requester_id, campaign_id, since, kinds, after, limit).model_dump(mode="json")

