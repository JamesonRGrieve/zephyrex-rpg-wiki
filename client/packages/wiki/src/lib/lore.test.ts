// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM. Held to the cases the server is held to (contract/lore-cases.json).
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/lore-cases.json';
import { lore, storedLore } from './lore';

describe('lore', () => {
  it.each(cases.valid.map((one) => [one.name, one] as const))('%s', (_name, one) => {
    expect(lore(one.value)).toEqual(one.checked);
  });

  it.each(cases.invalid.map((one) => [one.name, one] as const))('refuses %s', (_name, one) => {
    expect(() => lore(one.value)).toThrow(one.message);
  });

  it('reads back what was stored, and nothing from what can’t be read', () => {
    expect(storedLore('{"always_active":true}')?.order).toBe(100);
    expect(storedLore('{oops')).toBeNull();
    expect(storedLore(null)).toBeNull();
  });
});
