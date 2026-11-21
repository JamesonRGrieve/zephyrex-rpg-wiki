// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM. Held to the cases the server is held to (contract/disposition-cases.json).
import { describe, expect, it } from 'vitest';
import cases from '../../../contract/disposition-cases.json';
import { bandOf, currentAttitude } from './dispositions';

describe('currentAttitude', () => {
  it.each(cases.cases.map((one) => [one.name, one] as const))('%s', (_name, one) => {
    expect(currentAttitude(one.entries, one.resolved as Record<string, string>)).toBe(one.current);
  });
});

describe('bandOf', () => {
  it.each(cases.bands.map((one) => [one.attitude, one] as const))('%s', (_name, one) => {
    expect(bandOf(one.attitude)).toBe(one.band);
  });
});
