# SPDX-License-Identifier: AGPL-3.0-or-later
"""Zephyrex RPG Wiki's knowledge shared with the client: the kinds each record may take and the
limits on what it holds. It lives once, in contract/wiki.json at the repository root, which the
lite API and the front end read too (client/src/contract.ts). This module reads it."""

import json
from pathlib import Path
from typing import Any

# server/extensions/wiki_shared/Contract.py → the repository root, three levels up.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPOSITORY_ROOT / "contract" / "wiki.json"
ENTRY_TEXT_CASES_PATH = REPOSITORY_ROOT / "contract" / "entry-text-cases.json"
SLUG_CASES_PATH = REPOSITORY_ROOT / "contract" / "slug-cases.json"
KIT_CASES_PATH = REPOSITORY_ROOT / "contract" / "property-kit-cases.json"
NAME_LIST_CASES_PATH = REPOSITORY_ROOT / "contract" / "name-list-cases.json"
LORE_CASES_PATH = REPOSITORY_ROOT / "contract" / "lore-cases.json"
ENTITY_IDS_CASES_PATH = REPOSITORY_ROOT / "contract" / "entity-ids-cases.json"
PROVENANCE_CASES_PATH = REPOSITORY_ROOT / "contract" / "provenance-cases.json"
PICTURE_URL_CASES_PATH = REPOSITORY_ROOT / "contract" / "picture-url-cases.json"

CONTRACT: dict[str, Any] = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
LIMITS: dict[str, int] = CONTRACT["limits"]
PROVENANCES: tuple[str, ...] = tuple(CONTRACT["provenances"])
# The private property that keeps a record to the GM (the vault's is_private: true), "true" when set.
GM_ONLY_PROPERTY: str = CONTRACT["gm_only_property"]
# What a taxon can tag: the record kinds and campaigns (a scenario's play-style tags).
TAGGABLE_TYPES: tuple[str, ...] = tuple(CONTRACT["taggable_types"])
# The shared play-style tags (taxon kind play_style), seeded as SYSTEM's: everyone's to use.
SEED_PLAY_STYLES: tuple[str, ...] = tuple(CONTRACT["seed_play_styles"])
PLAY_STYLE = "play_style"
LOCATION_KINDS: tuple[str, ...] = tuple(CONTRACT["location_kinds"])
PERSON_KINDS: tuple[str, ...] = tuple(CONTRACT["person_kinds"])
FACTION_KINDS: tuple[str, ...] = tuple(CONTRACT["faction_kinds"])
ITEM_KINDS: tuple[str, ...] = tuple(CONTRACT["item_kinds"])
ENTITY_TYPES: tuple[str, ...] = tuple(CONTRACT["entity_types"])
JOURNAL_KINDS: tuple[str, ...] = tuple(CONTRACT["journal_kinds"])
HOOK_KINDS: tuple[str, ...] = tuple(CONTRACT["hook_kinds"])
TAXON_KINDS: tuple[str, ...] = tuple(CONTRACT["taxon_kinds"])
STATUS_KINDS: tuple[str, ...] = tuple(CONTRACT["status_kinds"])
ATTITUDES: tuple[str, ...] = tuple(CONTRACT["attitudes"])
ATTITUDE_NUANCES: dict[str, str] = dict(CONTRACT["attitude_nuances"])
DISPOSITION_TARGETS: tuple[str, ...] = tuple(CONTRACT["disposition_targets"])
CANON_LEVELS: tuple[str, ...] = tuple(CONTRACT["canon_levels"])
POST_POSITIONS: tuple[str, ...] = tuple(CONTRACT["post_positions"])
# How a property's value reads (S4b; the framework's record_metadata value types).
PROPERTY_VALUE_TYPES: tuple[str, ...] = tuple(CONTRACT["property_value_types"])
# S4d: lorebook activation, SillyTavern World Info's fields (positions and logic named, in ST's order).
LORE_POSITIONS: tuple[str, ...] = tuple(CONTRACT["lore_positions"])
LORE_LOGIC: tuple[str, ...] = tuple(CONTRACT["lore_logic"])
LORE_DEFAULTS: dict[str, Any] = dict(CONTRACT["lore_defaults"])
# What a file is to a record (S2c, the framework's attachments): the first is its own picture.
ATTACHMENT_ROLES: tuple[str, ...] = tuple(CONTRACT["attachment_roles"])
SETTING_SLUG_PATTERN: str = CONTRACT["setting_slug"]["pattern"]
SETTING_SLUG_CHARACTERS: int = CONTRACT["setting_slug"]["max_characters"]
# The settings every wiki has (S6b): SYSTEM's, so everyone reads them and nobody else changes them.
SEED_SETTINGS: tuple[dict[str, str], ...] = tuple(CONTRACT["seed_settings"])
