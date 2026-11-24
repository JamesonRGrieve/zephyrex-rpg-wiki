// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/framing-cases.json';
import { framingParts, publicEntry } from './framing';

describe('framingParts (contract/framing-cases.json)', () => {
  it.each(cases.splits)('splits: $name', ({ entry, public: open, gm }) => {
    expect(framingParts(entry)).toEqual({ public: open, gm });
    if (entry !== null) expect(framingParts(JSON.stringify(entry))).toEqual({ public: open, gm });
  });
});

describe('publicEntry: what a player may read of an entry', () => {
  const p = (text: string) => ({ type: 'p', children: [{ text }] });
  const h = (type: string, text: string) => ({ type, children: [{ text }] });

  it('leaves out each GM section, up to the next heading', () => {
    const entry = JSON.stringify([p('Keeps the inn.'), h('h2', 'GM secrets'), p('Lit the lighthouse.'), h('h2', 'History'), p('Born here.')]);
    expect(JSON.parse(publicEntry(entry) ?? 'null')).toEqual([p('Keeps the inn.'), h('h2', 'History'), p('Born here.')]);
  });

  it('keeps an entry with no GM section as it is, and answers null when nothing is left', () => {
    const open = JSON.stringify([p('Plain.')]);
    expect(publicEntry(open)).toBe(open);
    expect(publicEntry(JSON.stringify([h('h3', 'Behind the scenes'), p('All secret.')]))).toBeNull();
  });

  it('passes no entry, and text that is not an entry, through', () => {
    expect(publicEntry(null)).toBeNull();
    expect(publicEntry('')).toBe('');
    expect(publicEntry('not json')).toBe('not json');
  });
});
