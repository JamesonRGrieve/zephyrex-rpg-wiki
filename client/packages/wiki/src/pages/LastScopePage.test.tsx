// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import { lastScopePath } from './LastScopePage';

describe('lastScopePath', () => {
  it('opens the last scope, or Settings without one', () => {
    expect(lastScopePath('/w', null, 'person')).toBe('/w');
    expect(lastScopePath('/w', 'c1', 'person')).toBe('/w/c1/person');
    expect(lastScopePath('/w', 'setting-s1', 'journal')).toBe('/w/setting-s1/journal');
  });

  it('opens a campaign plot board, and a setting its game systems', () => {
    expect([lastScopePath('/w', 'c1', 'plot'), lastScopePath('/w', 'setting-s1', 'plot')]).toEqual(['/w/c1/plot', '/w']);
    expect([lastScopePath('/w', 'setting-s1', 'systems'), lastScopePath('/w', 'c1', 'systems')]).toEqual(['/w/setting-s1/location#game-systems-s1', '/w']);
  });
});
