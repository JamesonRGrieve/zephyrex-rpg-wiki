// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * What an app's own lite code does once a playthrough is made, as the server's rpg_core
 * AFTER_INSTANTIATE (rpg-ai copies the scenario's campaign frame; Parity, 2026-11-22). Each callback
 * hears the start once its copy has committed, in the order registered; one that fails is logged
 * and the rest go on: the playthrough stands either way.
 */

export interface Instantiated {
  ownerId: string;
  sourceCampaignId: string;
  newCampaignId: string;
  /** Every copied record's id (and the scenario's) → its copy's. */
  idMap: Readonly<Record<string, string>>;
}

export type AfterInstantiate = (started: Instantiated) => void | Promise<void>;

const callbacks: AfterInstantiate[] = [];

/** Registers a callback for every start; returns its unregistering. */
export function onAfterInstantiate(callback: AfterInstantiate): () => void {
  callbacks.push(callback);
  return () => {
    const at = callbacks.indexOf(callback);
    if (at >= 0) callbacks.splice(at, 1);
  };
}

/** Each registered callback, in turn; a failure is logged and passed over. */
export async function afterInstantiate(started: Instantiated): Promise<void> {
  for (const callback of [...callbacks]) {
    try {
      // eslint-disable-next-line no-await-in-loop -- in the order registered, as the server calls them
      await callback(started);
    } catch (error) {
      console.warn(`rpg_core lite: an after-instantiate callback failed for ${started.newCampaignId}:`, error);
    }
  }
}
