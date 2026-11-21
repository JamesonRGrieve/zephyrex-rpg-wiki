// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * What this deployment's back end can do, read from the back end itself: the same UI runs on the
 * lite and SaaS editions and never asks which one it is (docs/DESIGN.md, Editions). A feature turns
 * on when the extension serving it is listed (`GET /v1/extension`).
 */
import { useServerExtensions } from 'zephyrex';

export interface Capabilities {
  /** The back end's answer has arrived. */
  loaded: boolean;
  /** Worlds (rpg_core's campaigns). */
  worlds: boolean;
  /** Places (world_spatial). */
  places: boolean;
  /** People (genealogy). */
  people: boolean;
  /** Organisations and families (world_social). */
  factions: boolean;
  /** Items, and what anyone carries (world_inventory). */
  items: boolean;
  /** Journals: session reports, diaries, lore, notes (world_narrative). */
  journals: boolean;
  /** Plot hooks, their prerequisites and who is on them (world_narrative). */
  hooks: boolean;
  /** Tags, categories, races and statuses on any record (world_taxonomy). */
  taxonomy: boolean;
  /** Relations between people and organisations (genealogy's, widened by world_social). */
  relations: boolean;
  /** Posts on any record (entity_posts). */
  posts: boolean;
  /** A record's own key/values (the framework's metadata extension, S4b). */
  properties: boolean;
  /** Property kits, applied to a record's properties (world_properties, S4b). */
  kits: boolean;
  /** Accounts: the same records on every device the person signs in on. */
  accounts: boolean;
}

export function capabilitiesOf(names: ReadonlySet<string>, loaded: boolean): Capabilities {
  return {
    loaded,
    worlds: names.has('rpg_core'),
    places: names.has('world_spatial'),
    people: names.has('genealogy'),
    factions: names.has('world_social'),
    items: names.has('world_inventory'),
    journals: names.has('world_narrative'),
    hooks: names.has('world_narrative'),
    taxonomy: names.has('world_taxonomy'),
    relations: names.has('world_social') && names.has('genealogy'),
    posts: names.has('entity_posts'),
    properties: names.has('metadata'),
    kits: names.has('world_properties') && names.has('metadata'),
    accounts: names.has('auth_session'),
  };
}

export function useCapabilities(): Capabilities {
  const extensions = useServerExtensions();
  const names = new Set((extensions.data ?? []).map((extension) => extension.name));
  return capabilitiesOf(names, extensions.data !== undefined);
}
