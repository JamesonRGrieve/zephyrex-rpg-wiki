// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The world's activation index, as the server's wiki_shared/WorldKeys.py
 * (contract/world-keys-cases.json): a record's keys and the keys a text holds, so a narrator's turn
 * reads only the records its text names.
 */
export const ALWAYS = '*';
const MAX_WORDS = 8;

export function normalised(text: string): string {
  return (text ?? '')
    .normalize('NFKD')
    .replace(/\p{M}+/gu, '')
    .toLocaleLowerCase('en')
    .replace(/[^0-9a-z]+/g, ' ')
    .trim();
}

export function recordKeys(name: string, aliases: readonly string[], keywords: readonly string[], alwaysActive: boolean): string[] {
  const keys = new Set<string>(alwaysActive ? [ALWAYS] : []);
  for (const raw of [name, ...aliases, ...keywords]) {
    const text = String(raw ?? '').trim();
    if (text.length > 1 && text.startsWith('/') && text.endsWith('/')) continue;
    const key = normalised(text);
    if (key.length >= 2 && key.split(' ').length <= MAX_WORDS) keys.add(key);
  }
  return [...keys].sort();
}

export function textGrams(text: string): Set<string> {
  const words = normalised(text).split(' ').filter((word) => word !== '');
  const grams = new Set<string>();
  for (let start = 0; start < words.length; start += 1) {
    for (let size = 1; size <= MAX_WORDS && start + size <= words.length; size += 1) grams.add(words.slice(start, start + size).join(' '));
  }
  return grams;
}
