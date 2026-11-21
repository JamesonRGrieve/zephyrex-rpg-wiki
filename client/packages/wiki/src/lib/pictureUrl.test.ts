// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/picture-url-cases.json';
import { pictureUrl } from './pictureUrl';

describe('pictureUrl (contract/picture-url-cases.json)', () => {
  it.each(cases.valid)('reads $name', ({ value, url }) => {
    expect(pictureUrl(value)).toBe(url);
  });

  it.each(cases.invalid)('refuses $name', ({ value, message }) => {
    expect(() => pictureUrl(value)).toThrow(message);
  });
});
