// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/provenance-cases.json';
import { provenance } from './provenance';

describe('provenance (contract/provenance-cases.json)', () => {
  it.each(cases.valid)('reads $name', ({ value, checked }) => {
    expect(provenance(value)).toEqual(checked);
  });

  it.each(cases.invalid)('refuses $name', ({ value, message }) => {
    expect(() => provenance(value)).toThrow(message);
  });
});
