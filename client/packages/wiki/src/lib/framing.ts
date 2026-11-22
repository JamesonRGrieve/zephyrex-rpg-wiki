// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A campaign's framing entry split into its public text and its GM part, as the server's
 * wiki_shared/Framing.py (contract/framing-cases.json): the title (h1) left out; each h2-h6 heading
 * opens a section, the GM's when its heading names the GM, a game master, secrets or what's behind
 * the scenes; text before any heading is public.
 */
import { plainText } from './entry';

const GM_HEADING = /\b(gm|game ?master|secrets?|behind the scenes)\b/i;
const HEADINGS = new Set(['h2', 'h3', 'h4', 'h5', 'h6']);

export function framingParts(entry: unknown): { public: string; gm: string } {
  let blocks = entry;
  if (typeof blocks === 'string' && blocks !== '') blocks = JSON.parse(blocks) as unknown;
  if (!Array.isArray(blocks)) return { public: '', gm: '' };
  const open: string[][] = [[]];
  const kept: string[][] = [];
  let into = open[0]!;
  for (const block of blocks) {
    if (block === null || typeof block !== 'object') continue;
    const kind = (block as { type?: unknown }).type;
    const text = plainText([block]).trim();
    if (kind === 'h1') continue;
    if (typeof kind === 'string' && HEADINGS.has(kind)) {
      into = text ? [text] : [];
      (GM_HEADING.test(text) ? kept : open).push(into);
      continue;
    }
    if (text) into.push(text);
  }
  const joined = (sections: string[][]): string =>
    sections
      .filter((lines) => lines.length > 0)
      .map((lines) => lines.join('\n'))
      .join('\n\n');
  return { public: joined(open), gm: joined(kept) };
}
