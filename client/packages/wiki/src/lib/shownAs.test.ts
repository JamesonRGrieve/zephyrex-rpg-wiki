// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import { entryWithoutName, withoutName } from './shownAs';

const bastian = { names: ['Lord Bastian Ashgrove', 'Bash'], shownAs: 'a human heir' };

describe('withoutName', () => {
  it('reads each of the names as the description, whatever its case', () => {
    expect(withoutName('Lord Bastian Ashgrove waits. LORD BASTIAN ASHGROVE bows.', bastian)).toBe('a human heir waits. a human heir bows.');
    expect(withoutName('They call him Bash.', bastian)).toBe('They call him a human heir.');
  });

  it('hides a word of the name left alone, never a title or a longer word', () => {
    expect(withoutName("Bastian's aunt left Ashgrove Manor to the Lord.", bastian)).toBe("…'s aunt left … Manor to the Lord.");
    expect(withoutName('Ashgroves and Bastiany stay.', bastian)).toBe('Ashgroves and Bastiany stay.');
  });

  it('leaves text with none of the names as it is', () => {
    expect(withoutName('Keeps the Lantern House.', bastian)).toBe('Keeps the Lantern House.');
    expect(withoutName('Anything.', { names: ['', '  '], shownAs: 'someone' })).toBe('Anything.');
  });
});

describe('entryWithoutName', () => {
  it('reads every text node of an entry, mentions included', () => {
    const entry = JSON.stringify([
      { type: 'h2', children: [{ text: 'Bastian Ashgrove' }] },
      { type: 'p', children: [{ text: 'Heir of the house.' }, { type: 'mention', target_entity_id: 'p1', children: [{ text: 'Lord Bastian Ashgrove' }] }] },
    ]);
    expect(JSON.parse(entryWithoutName(entry, bastian) ?? '')).toEqual([
      { type: 'h2', children: [{ text: '… …' }] },
      { type: 'p', children: [{ text: 'Heir of the house.' }, { type: 'mention', target_entity_id: 'p1', children: [{ text: 'a human heir' }] }] },
    ]);
  });

  it('reads text that is not an entry as plain text, and none as none', () => {
    expect(entryWithoutName('Bastian waits.', bastian)).toBe('… waits.');
    expect(entryWithoutName(null, bastian)).toBeNull();
    expect(entryWithoutName('', bastian)).toBe('');
  });
});
