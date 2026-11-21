// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM. Held to the cases the server is held to (contract/name-list-cases.json).
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/name-list-cases.json';
import { names, storedNames, storedVoice, voice } from './names';

describe('names', () => {
  it.each(cases.lists.map((one) => [one.name, one] as const))('%s', (_name, one) => {
    expect(names(one.value)).toEqual(one.checked);
  });

  it.each(cases.invalid_lists.map((one) => [one.name, one] as const))('refuses %s', (_name, one) => {
    expect(() => names(one.value)).toThrow(one.message);
  });

  it('holds a list to fifty names', () => {
    expect(() => names(Array.from({ length: 51 }, (_, index) => `n${index}`))).toThrow(/at most 50/);
  });
});

describe('voice', () => {
  it.each(cases.voices.map((one) => [one.name, one] as const))('%s', (_name, one) => {
    expect(voice(one.value)).toEqual(one.checked);
  });

  it.each(cases.invalid_voices.map((one) => [one.name, one] as const))('refuses %s', (_name, one) => {
    expect(() => voice(one.value)).toThrow(one.message);
  });
});

describe('stored values', () => {
  it('reads what was stored, and nothing from what can’t be read', () => {
    expect(storedNames('["A","B"]')).toEqual(['A', 'B']);
    expect(storedNames('{oops')).toEqual([]);
    expect(storedVoice(null)).toBeNull();
    expect(storedVoice('{"personality":"Kind"}')).toEqual({ personality: 'Kind', speech: '', first_message: '', examples: [] });
  });
});
