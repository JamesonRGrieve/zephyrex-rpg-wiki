// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/era-cases.json';
import { eraVisible } from './eras';

describe('eraVisible (contract/era-cases.json)', () => {
  it.each(cases.cases)('$name', ({ record, campaign, visible }) => {
    expect(eraVisible(record, campaign)).toBe(visible);
  });
});
