// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Whom a person regards how, now (W56, from dh-campaign's tracker), the same rule as the server's
 * (server/extensions/wiki_shared/Dispositions.py), held to contract/disposition-cases.json.
 *
 * Toward one target, a person has one default entry and any number with a trigger hook. The current
 * attitude is the entry whose trigger was resolved most recently (a later entry wins a tie), else
 * the default, else none. A nuance attitude reads as its band wherever only the scale is understood.
 */
import { ATTITUDE_NUANCES } from '~/contract';

export interface DispositionEntry {
  attitude: string;
  default: boolean;
  trigger: string | null;
}

/** The scale's attitude a nuance reads as; a scale attitude reads as itself. */
export function bandOf(attitude: string): string {
  return ATTITUDE_NUANCES[attitude] ?? attitude;
}

/** The current attitude from the entries and when each resolved hook was resolved (ISO stamps). */
export function currentAttitude(entries: readonly DispositionEntry[], resolved: Readonly<Record<string, string>>): string | null {
  let best: { at: string; index: number } | null = null;
  let chosen: string | null = null;
  for (const [index, entry] of entries.entries()) {
    const at = entry.trigger === null ? undefined : resolved[entry.trigger];
    if (at === undefined) continue;
    if (best === null || at > best.at || (at === best.at && index >= best.index)) {
      best = { at, index };
      chosen = entry.attitude;
    }
  }
  if (chosen !== null) return chosen;
  const defaults = entries.filter((entry) => entry.default);
  return defaults.at(-1)?.attitude ?? null;
}
