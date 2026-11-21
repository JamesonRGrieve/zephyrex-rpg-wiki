// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM, so no jsdom to load (which, read from an NFS store, can miss Vitest's worker start).
// An entry's plain-text copy, held to the cases the server is held to
// (contract/entry-text-cases.json; server/extensions/wiki_shared/Entry_test.py).
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/entry-text-cases.json';
import { LIMITS } from '../contract';
import { EntryError, parseEntry, plainText } from './entry';

describe('plainText', () => {
  it.each(cases.cases.map((one) => [one.name, one] as const))('%s', (_name, one) => {
    expect(plainText(one.entry)).toBe(one.text);
  });

  it.each(cases.refusals.map((one) => [one.name, one] as const))('refuses %s', (_name, one) => {
    expect(() => plainText(one.entry)).toThrow(EntryError);
  });
});

describe('parseEntry', () => {
  const value = cases.cases[1]?.entry;

  it('takes the value or its JSON text, and gives the same answer', () => {
    expect(parseEntry(value)).toEqual(parseEntry(JSON.stringify(value)));
    expect(parseEntry(value).text).toBe('A port city.');
  });

  it('refuses JSON text that does not parse', () => {
    expect(() => parseEntry('{not json')).toThrow(EntryError);
  });

  it('refuses an entry past the size limit', () => {
    const big = [{ type: 'p', children: [{ text: 'x'.repeat(LIMITS.entry_bytes + 1) }] }];
    expect(() => parseEntry(big)).toThrow(EntryError);
  });

  it('refuses an entry nested past the depth limit', () => {
    let node: object = { text: 'deep' };
    for (let level = 0; level <= LIMITS.entry_depth; level += 1) node = { type: 'div', children: [node] };
    expect(() => plainText([node])).toThrow(EntryError);
  });
});
