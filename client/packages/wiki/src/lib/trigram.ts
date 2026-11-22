// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * pg_trgm's word_similarity, for lite's trigram rank (the server asks Postgres): how well ``needle``
 * matches the most similar run of words in ``haystack``, from 0 to 1. Trigrams as pg_trgm makes
 * them: each word lower-cased, padded with two spaces before and one after.
 */
function wordsOf(text: string): string[] {
  return text.toLocaleLowerCase().split(/[^\p{L}\p{N}]+/u).filter((word) => word !== '');
}

function trigrams(words: readonly string[]): Set<string> {
  const found = new Set<string>();
  for (const word of words) {
    const padded = `  ${word} `;
    for (let index = 0; index + 3 <= padded.length; index += 1) found.add(padded.slice(index, index + 3));
  }
  return found;
}

function similarity(one: Set<string>, two: Set<string>): number {
  let shared = 0;
  for (const gram of one) if (two.has(gram)) shared += 1;
  const union = one.size + two.size - shared;
  return union === 0 ? 0 : shared / union;
}

export const WORD_SIMILARITY_THRESHOLD = 0.6; // pg_trgm.word_similarity_threshold's default

export function wordSimilarity(needle: string, haystack: string): number {
  const wanted = wordsOf(needle);
  const words = wordsOf(haystack);
  if (wanted.length === 0 || words.length === 0) return 0;
  const target = trigrams(wanted);
  let best = 0;
  for (const size of [wanted.length - 1, wanted.length, wanted.length + 1]) {
    if (size < 1) continue;
    for (let start = 0; start + size <= words.length; start += 1) best = Math.max(best, similarity(target, trigrams(words.slice(start, start + size))));
    if (size > words.length) best = Math.max(best, similarity(target, trigrams(words)));
  }
  return best;
}
