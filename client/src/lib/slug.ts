// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A setting's slug (S6b, contract/wiki.json setting_slug), as the server's wiki_shared/Records.py
 * derives and checks it; both are held to contract/slug-cases.json.
 */
import { SETTING_SLUG } from '~/contract';

const PATTERN = new RegExp(SETTING_SLUG.pattern);
const MAX = SETTING_SLUG.max_characters;

/** What a slug may be, in words: the message both editions give. */
export const SLUG_RULE = `A slug is lower-case letters and digits in words joined by single hyphens, at most ${MAX} characters`;

const trimHyphens = (text: string): string => text.replace(/^-+|-+$/g, '');

/** Lower case, every other run of characters one hyphen, at most the contract's length; "unnamed" when nothing is left. */
export function slugify(name: string): string {
  return trimHyphens(trimHyphens(name.toLowerCase().replace(/[^a-z0-9]+/g, '-')).slice(0, MAX)) || 'unnamed';
}

/** `slug`, or with the first -2, -3… not taken, still within the contract's length. */
export function freeSlug(slug: string, isTaken: (candidate: string) => boolean): string {
  if (!isTaken(slug)) return slug;
  for (let number = 2; ; number += 1) {
    const suffix = `-${number}`;
    const candidate = `${slug.slice(0, MAX - suffix.length).replace(/-+$/, '')}${suffix}`;
    if (!isTaken(candidate)) return candidate;
  }
}

/** Whether the contract allows `slug`. */
export function isSlug(slug: string): boolean {
  return slug.length <= MAX && PATTERN.test(slug);
}
