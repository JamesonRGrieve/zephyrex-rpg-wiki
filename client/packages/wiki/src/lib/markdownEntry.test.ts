// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/markdown-entry-cases.json';
import { markdownEntry } from './markdownEntry';

describe('markdownEntry (contract/markdown-entry-cases.json)', () => {
  it.each(cases.entries)('reads: $name', ({ markdown, entry }) => {
    expect(markdownEntry(markdown)).toEqual(entry);
  });
});
