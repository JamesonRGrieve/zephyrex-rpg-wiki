// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM. Held to the cases the server is held to (contract/property-kit-cases.json).
import { describe, expect, it } from 'vitest';
import cases from '../../../contract/property-kit-cases.json';
import { checkedKit, KitError } from './properties';

describe('checkedKit', () => {
  it.each(cases.valid.map((one) => [one.name, one] as const))('normalises %s', (_name, one) => {
    expect(checkedKit(one.properties)).toEqual(one.checked);
  });

  it.each(cases.invalid.map((one) => [one.name, one] as const))('refuses %s', (_name, one) => {
    expect(() => checkedKit(one.properties)).toThrow(new KitError(one.message));
  });

  it('holds a kit to a record’s keys', () => {
    expect(() => checkedKit(Array.from({ length: 201 }, (_, index) => ({ key: `k${index}` })))).toThrow(/at most 200/);
  });
});
