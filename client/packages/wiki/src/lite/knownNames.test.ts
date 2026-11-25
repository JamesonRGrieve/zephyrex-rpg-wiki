// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import { knownNamesOf } from './knownNames';

describe('knownNamesOf (as the server rpg_core known_names)', () => {
  it('a PC knows the party and whom they know of; a fact with text alone is no name', () => {
    const names = knownNamesOf(
      ['wren', 'tam'],
      [
        { personId: 'tam', targetEntityType: 'person', targetEntityId: 'mags', text: null },
        { personId: 'wren', targetEntityType: 'person', targetEntityId: 'brom', text: 'The dwarf at the bar pours short.' },
        { personId: 'tam', targetEntityType: 'location', targetEntityId: 'keep', text: null },
        { personId: 'tam', targetEntityType: 'person', targetEntityId: 'quill', text: '   ' },
      ],
    );
    expect(names).toEqual({ party: ['mags', 'quill', 'tam', 'wren'], by_pc: { tam: ['mags', 'quill', 'tam', 'wren'], wren: ['tam', 'wren'] } });
  });

  it('a person known to the party is known to every PC', () => {
    expect(knownNamesOf(['tam', 'wren'], [], ['bastian'])).toEqual({ party: ['bastian', 'tam', 'wren'], by_pc: { tam: ['bastian', 'tam', 'wren'], wren: ['bastian', 'tam', 'wren'] } });
  });

  it('no party, no names', () => {
    expect(knownNamesOf([], [{ personId: 'x', targetEntityType: 'person', targetEntityId: 'y', text: null }])).toEqual({ party: [], by_pc: {} });
  });
});
