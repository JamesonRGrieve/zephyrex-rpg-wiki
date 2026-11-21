// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import { aboutPath, kindPath, plotPath, recordPath, taxonomyPath, wikiRoot } from './paths';

describe('wiki paths', () => {
  it('reads the base with or without slashes', () => {
    expect(['w', '/w', '/w/', 'wiki/'].map(wikiRoot)).toEqual(['/w', '/w', '/w', '/wiki']);
  });

  it('builds every page path under the base', () => {
    expect(kindPath('w', 'c1', 'person')).toBe('/w/c1/person');
    expect(recordPath('/wiki', 'c1', 'item', 'i 2')).toBe('/wiki/c1/item/i%202');
    expect([taxonomyPath('w', 'c1'), taxonomyPath('w', 'c1', 't9')]).toEqual(['/w/c1/taxonomy', '/w/c1/taxonomy?taxon=t9']);
    expect(plotPath('w', 'c1')).toBe('/w/c1/plot');
    expect(aboutPath('w', 'c1')).toBe('/w/c1/about');
  });
});
