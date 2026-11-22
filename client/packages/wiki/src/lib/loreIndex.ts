// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The lore index's shared rules, as the server's wiki_shared/LoreIndex.py
 * (contract/lore-index-cases.json): passages cut from a record's entry, a campaign's scope over
 * chunks, reciprocal rank fusion with exact name hits first, and packing to a token budget.
 */
import { plainText } from './entry';

export const RRF_K = 60;

export const tokens = (text: string): number => Math.ceil((text ?? '').length / 4);

function pieces(text: string, maxTokens: number): string[] {
  if (tokens(text) <= maxTokens) return [text];
  const out: string[] = [];
  for (const sentence of text.split(/(?<=[.!?])\s+/)) {
    if (tokens(sentence) <= maxTokens) {
      out.push(sentence);
      continue;
    }
    let words: string[] = [];
    for (const word of sentence.split(/\s+/).filter((one) => one !== '')) {
      if (words.length > 0 && tokens([...words, word].join(' ')) > maxTokens) {
        out.push(words.join(' '));
        words = [];
      }
      words.push(word);
    }
    if (words.length > 0) out.push(words.join(' '));
  }
  return out;
}

export interface Passage {
  path: string[];
  text: string;
}

export function chunkEntry(record: string, entry: unknown, maxTokens = 600, minTokens = 300): Passage[] {
  let blocks = entry;
  if (typeof blocks === 'string' && blocks !== '') blocks = JSON.parse(blocks) as unknown;
  const passages: Passage[] = [];
  const stack: [number, string][] = [];
  let current: string[] = [];
  const close = (): void => {
    if (current.length > 0) passages.push({ path: [record, ...stack.map(([, text]) => text)], text: current.join('\n') });
    current = [];
  };
  for (const block of Array.isArray(blocks) ? blocks : []) {
    if (block === null || typeof block !== 'object') continue;
    const heading = /^h([1-6])$/.exec(String((block as { type?: unknown }).type ?? ''));
    const text = plainText([block]).trim();
    if (heading) {
      close();
      const level = Number(heading[1]);
      while (stack.length > 0 && stack[stack.length - 1]![0] >= level) stack.pop();
      if (text) stack.push([level, text]);
      continue;
    }
    for (const piece of text ? pieces(text, maxTokens) : []) {
      if (current.length > 0 && tokens([...current, piece].join('\n')) > maxTokens) close();
      current.push(piece);
      if (tokens(current.join('\n')) >= minTokens) close();
    }
  }
  close();
  return passages;
}

type Scoped = { campaign_id?: string | null; setting_id?: string | null; game_system_id?: string | null };
type Campaign = { id: string; scenario_id?: string | null; setting_id?: string | null; game_system_id?: string | null };

export function inScope(campaign: Campaign, chunk: Scoped): boolean {
  if (chunk.campaign_id) return chunk.campaign_id === campaign.id || chunk.campaign_id === campaign.scenario_id;
  if (!chunk.setting_id || chunk.setting_id !== campaign.setting_id) return false;
  return !chunk.game_system_id || chunk.game_system_id === campaign.game_system_id;
}

export function fuse(rankings: Record<string, readonly string[]>, exact: readonly string[] = [], k = RRF_K): [string, number][] {
  const scores = new Map<string, number>();
  for (const ranking of Object.values(rankings)) ranking.forEach((one, index) => scores.set(one, (scores.get(one) ?? 0) + 1 / (k + index + 1)));
  const first = [...new Set(exact)];
  const rest = [...scores.keys()].filter((one) => !first.includes(one)).sort((a, b) => (scores.get(b) ?? 0) - (scores.get(a) ?? 0) || (a < b ? -1 : a > b ? 1 : 0));
  return [...first, ...rest].map((one) => [one, scores.get(one) ?? 0]);
}

export function pack<T extends { tokens?: number }>(chunks: readonly T[], budget: number): T[] {
  let left = budget;
  const kept: T[] = [];
  for (const one of chunks) {
    const size = one.tokens ?? 0;
    if (size <= left) {
      kept.push(one);
      left -= size;
    }
  }
  return kept;
}
