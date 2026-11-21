// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/entity-ids-cases.json';
import { entityIds } from './entityIds';

describe('entityIds (contract/entity-ids-cases.json)', () => {
  it.each(cases.valid)('reads $name', ({ query, ids }) => {
    expect(entityIds(query.split(','))).toEqual(ids);
  });

  it.each(cases.invalid)('refuses $name', ({ query, error }) => {
    expect(() => entityIds(query.split(','))).toThrow(error);
  });
});
