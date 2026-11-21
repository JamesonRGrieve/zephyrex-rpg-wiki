// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The wiki's page paths (S7), the one place they're built: its own pages use them, and an app that
 * composes the wiki links into it with them (vtt's tokens, seats and sheets to a record's page).
 * `base` is where the pages are mounted (`wikiExtension({ base })`: "w" by default; a leading or
 * trailing slash is fine). Kinds are the record kinds: location, person, faction, item, journal,
 * hook.
 */

/** The base as a path: "w", "/w/" and "/w" all give "/w". */
export function wikiRoot(base: string): string {
  return `/${base.replace(/^\/+|\/+$/g, '')}`;
}

const part = (value: string): string => encodeURIComponent(value);

/** One world's records of a kind: /w/<world>/<kind>. */
export function kindPath(base: string, world: string, kind: string): string {
  return `${wikiRoot(base)}/${part(world)}/${part(kind)}`;
}

/** A record's page: /w/<world>/<kind>/<id>. */
export function recordPath(base: string, world: string, kind: string, id: string): string {
  return `${kindPath(base, world, kind)}/${part(id)}`;
}

/** A world's tags, or one tag's records: /w/<world>/taxonomy[?taxon=<id>]. */
export function taxonomyPath(base: string, world: string, taxon?: string): string {
  const path = `${wikiRoot(base)}/${part(world)}/taxonomy`;
  return taxon === undefined ? path : `${path}?taxon=${part(taxon)}`;
}

/** A world's plot board: /w/<world>/plot. */
export function plotPath(base: string, world: string): string {
  return `${wikiRoot(base)}/${part(world)}/plot`;
}
