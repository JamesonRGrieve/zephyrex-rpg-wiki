// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/unnamed-as-cases.json';
import { genericUnnamed, unnamedAs } from './names';

describe('unnamedAs (contract/unnamed-as-cases.json)', () => {
  it.each(cases.stored)('$name', (one) => {
    if ('error' in one && one.error) expect(() => unnamedAs(one.value)).toThrow(one.error);
    else expect(unnamedAs(one.value)).toBe('stored' in one ? one.stored : null);
  });
});

describe('genericUnnamed (contract/unnamed-as-cases.json)', () => {
  it.each(cases.generic)('$name', (one) => {
    expect(genericUnnamed(one.species, one.role, one.gender)).toBe(one.generic);
  });
});
