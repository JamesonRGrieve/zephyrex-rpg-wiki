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
    accounts: names.has('auth_session'),
  };
}

export function useCapabilities(): Capabilities {
  const extensions = useServerExtensions();
  const names = new Set((extensions.data ?? []).map((extension) => extension.name));
  return capabilitiesOf(names, extensions.data !== undefined);
}
