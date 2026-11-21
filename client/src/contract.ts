// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Zephyrex RPG Wiki's knowledge shared with the server: the kinds each record may take and the
 * limits on what it holds. It lives once, in contract/wiki.json at the repository root, which the
 * server reads too (server/extensions/wiki_shared/Contract.py). Nothing here restates it.
 */
import contract from '../../contract/wiki.json';

export const LIMITS = contract.limits;
export const LOCATION_KINDS = contract.location_kinds as readonly string[];
export const PERSON_KINDS = contract.person_kinds as readonly string[];
export const ENTITY_TYPES = contract.entity_types as readonly string[];
export const FACTION_KINDS = contract.faction_kinds as readonly string[];
export const ITEM_KINDS = contract.item_kinds as readonly string[];
export const JOURNAL_KINDS = contract.journal_kinds as readonly string[];
export const HOOK_KINDS = contract.hook_kinds as readonly string[];
export const TAXON_KINDS = contract.taxon_kinds as readonly string[];
export const STATUS_KINDS = contract.status_kinds as readonly string[];
export const ATTITUDES = contract.attitudes as readonly string[];
export const ATTITUDE_NUANCES = contract.attitude_nuances as Readonly<Record<string, string>>;
export const DISPOSITION_TARGETS = contract.disposition_targets as readonly string[];
export const CANON_LEVELS = contract.canon_levels as readonly string[];
export const POST_POSITIONS = contract.post_positions as readonly string[];
export const SETTING_SLUG = contract.setting_slug;
/** How a property's value reads (S4b; the framework's record_metadata value types). */
export const PROPERTY_VALUE_TYPES = contract.property_value_types as readonly string[];
/** What a file is to a record (S2c): the first is its own picture. */
export const ATTACHMENT_ROLES = contract.attachment_roles as readonly string[];
/** The settings every wiki has (S6b): the system's, so everyone reads them and nobody else changes them. */
export const SEED_SETTINGS = contract.seed_settings as readonly { slug: string; name: string }[];
