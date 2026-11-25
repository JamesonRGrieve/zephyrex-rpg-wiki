// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A person's page shown by a description, not their name (operator, 2026-11-25: "If they're a
 * character they should be tagged and act as one, if we don't know their name. Their character page
 * should still work."): rpg-ai opens an unnamed person's page with `shownAs` (their unnamed_as), and
 * the page keeps every word of their name out of what it shows. Each of their names (the name and
 * each alias) reads as the description; any word left of them (a given name alone, a surname) reads
 * as "…". Titles and joining words ("Lord", "of") are left as they are.
 */

/** Words of a name that say nothing of who someone is, left in the text. */
const KEPT_WORDS = new Set([
  'lord', 'lady', 'sir', 'dame', 'master', 'mistress', 'mister', 'mrs', 'mr', 'ms', 'miss', 'madam', 'captain',
  'father', 'mother', 'brother', 'sister', 'the', 'of', 'von', 'van', 'de', 'du', 'la', 'le', 'and', 'old', 'young',
]);
const HIDDEN = '…';

function escaped(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** A word or phrase as a pattern that matches it whole (not inside a longer word). */
function whole(text: string, flags: string): RegExp {
  return new RegExp(`(?<![\\p{L}\\p{N}])${escaped(text)}(?![\\p{L}\\p{N}])`, flags);
}

export interface Naming {
  /** The person's names: their name, then each alias. */
  names: readonly string[];
  /** What the page calls them instead. */
  shownAs: string;
}

/** `text` with each of the person's names read as their description and any word of a name left
 * read as "…". */
export function withoutName(text: string, { names, shownAs }: Naming): string {
  const full = [...new Set(names.map((one) => one.trim()).filter((one) => one !== ''))].sort((one, two) => two.length - one.length);
  let out = text;
  for (const one of full) out = out.replace(whole(one, 'giu'), shownAs);
  const parts = [...new Set(full.flatMap((one) => one.split(/[\s,]+/)).filter((word) => word.length >= 2 && !KEPT_WORDS.has(word.toLowerCase())))].sort(
    (one, two) => two.length - one.length,
  );
  for (const word of parts) out = out.replace(whole(word, 'gu'), HIDDEN);
  return out;
}

/** A stored entry (Plate JSON text) with every text node read through withoutName; text that isn't
 * an entry reads as plain text. */
export function entryWithoutName(entry: string | null, naming: Naming): string | null {
  if (entry === null || entry === '') return entry;
  let blocks: unknown;
  try {
    blocks = JSON.parse(entry) as unknown;
  } catch {
    return withoutName(entry, naming);
  }
  const walk = (node: unknown): unknown => {
    if (Array.isArray(node)) return node.map(walk);
    if (node !== null && typeof node === 'object') {
      return Object.fromEntries(Object.entries(node as Record<string, unknown>).map(([key, value]) => [key, key === 'text' && typeof value === 'string' ? withoutName(value, naming) : walk(value)]));
    }
    return node;
  };
  return JSON.stringify(walk(blocks));
}
