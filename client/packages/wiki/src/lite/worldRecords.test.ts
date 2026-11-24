// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
/** A lite list's filters, as the framework's LIST reads them: equality, and `<field>__in`. */
import { ApiError } from '@zephyrex/lite';
import { describe, expect, it } from 'vitest';
import { filters } from './worldRecords';

const query = (text: string) => new URLSearchParams(text);
const NAMES: [string, string][] = [['campaign_id', 'campaignId']];

describe('filters', () => {
  it('reads a named field by equality', () => {
    expect(filters(query('campaign_id=c1'), NAMES)).toEqual({ campaignId: 'c1' });
  });

  it('reads id__in and a named field__in as one of their values, trimmed, empties and repeats dropped', () => {
    expect(filters(query('id__in=a, b,,a&campaign_id__in=c1,c2'), NAMES)).toEqual({ id: { in: ['a', 'b'] }, campaignId: { in: ['c1', 'c2'] } });
  });

  it('refuses more than 100 values (422)', () => {
    const many = Array.from({ length: 101 }, (_value, index) => `r${String(index)}`).join(',');
    expect(() => filters(query(`id__in=${many}`), NAMES)).toThrow(ApiError);
  });

  it('ignores a field it does not name', () => {
    expect(filters(query('kind__in=a,b'), NAMES)).toEqual({});
  });
});
