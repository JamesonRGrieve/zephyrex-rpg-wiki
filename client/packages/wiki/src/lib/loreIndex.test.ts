// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/lore-index-cases.json';
import { chunkEntry, fuse, inScope, pack, tokens } from './loreIndex';

describe('loreIndex (contract/lore-index-cases.json)', () => {
  it.each(cases.tokens)('counts tokens: $name', ({ text, tokens: expected }) => {
    expect(tokens(text)).toBe(expected);
  });
  it.each(cases.chunks)('cuts passages: $name', ({ record, entry, max_tokens, min_tokens, passages }) => {
    expect(chunkEntry(record, entry, max_tokens, min_tokens)).toEqual(passages);
  });
  it.each(cases.scopes)("keeps to the campaign's scope: $name", ({ campaign, chunks, visible }) => {
    expect(chunks.filter((chunk) => inScope(campaign, chunk)).map((chunk) => chunk.id)).toEqual(visible);
  });
  it.each(cases.fusions)('fuses rankings: $name', ({ rankings, exact, order }) => {
    expect(fuse(rankings, exact).map(([one]) => one)).toEqual(order);
  });
  it.each(cases.packs)('packs to a budget: $name', ({ budget, chunks, packed }) => {
    expect(pack(chunks, budget).map((chunk) => chunk.id)).toEqual(packed);
  });
});
