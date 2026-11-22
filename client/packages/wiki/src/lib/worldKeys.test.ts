// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/world-keys-cases.json';
import { normalised, recordKeys, textGrams } from './worldKeys';

describe('worldKeys (contract/world-keys-cases.json)', () => {
  it.each(cases.normalised)('normalises: $name', ({ value, normalised: expected }) => {
    expect(normalised(value)).toBe(expected);
  });
  it.each(cases.keys)("a record's keys: $name", ({ record, keys }) => {
    expect(recordKeys(record.name, record.aliases, record.keywords, record.always_active)).toEqual(keys);
  });
  it.each(cases.matches)('a text matches: $name', ({ text, keys, matched }) => {
    const grams = textGrams(text);
    expect(keys.filter((key) => grams.has(key)).sort()).toEqual(matched);
  });
});
