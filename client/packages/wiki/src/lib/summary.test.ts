// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM, so no jsdom to load (which, read from an NFS store, can miss Vitest's worker start).
// A record's summary, held to the cases the server and rpg-ai are held to (contract/summary-cases.json).
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/summary-cases.json';
import { LIMITS } from '../contract';
import { summary } from './summary';

describe('summary', () => {
  it.each(cases.cases.map((one) => [one.name, one] as const))('%s', (_name, one) => {
    expect(summary(one.text, cases.limit)).toBe(one.summary);
  });

  it('never exceeds the contract limit', () => {
    expect(summary('word '.repeat(500)).length).toBeLessThanOrEqual(LIMITS.summary_characters);
  });
});
