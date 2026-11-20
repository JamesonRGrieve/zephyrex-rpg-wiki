# SPDX-License-Identifier: AGPL-3.0-or-later
"""Zephyrex RPG Wiki's knowledge shared with the client: the kinds each record may take and the
limits on what it holds. It lives once, in contract/wiki.json at the repository root, which the
lite API and the front end read too (client/src/contract.ts). This module reads it."""

import json
from pathlib import Path
from typing import Any

# server/extensions/world_spatial/Contract.py → the repository root, three levels up.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPOSITORY_ROOT / "contract" / "wiki.json"
ENTRY_TEXT_CASES_PATH = REPOSITORY_ROOT / "contract" / "entry-text-cases.json"

CONTRACT: dict[str, Any] = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
LIMITS: dict[str, int] = CONTRACT["limits"]
LOCATION_KINDS: tuple[str, ...] = tuple(CONTRACT["location_kinds"])
PERSON_KINDS: tuple[str, ...] = tuple(CONTRACT["person_kinds"])
