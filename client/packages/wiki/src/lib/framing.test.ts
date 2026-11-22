// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/framing-cases.json';
import { framingParts } from './framing';

describe('framingParts (contract/framing-cases.json)', () => {
  it.each(cases.splits)('splits: $name', ({ entry, public: open, gm }) => {
    expect(framingParts(entry)).toEqual({ public: open, gm });
    if (entry !== null) expect(framingParts(JSON.stringify(entry))).toEqual({ public: open, gm });
  });
});
