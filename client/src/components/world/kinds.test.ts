// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import { FACTION_KINDS, ITEM_KINDS, LOCATION_KINDS, PERSON_KINDS } from '~/contract';
import { ENTITY_KINDS, isEntityKind } from './kinds';

describe('ENTITY_KINDS', () => {
  it('names the kinds of record a world lists, with the contract’s kinds', () => {
    expect(Object.keys(ENTITY_KINDS)).toEqual(['location', 'person', 'faction', 'item']);
    expect(ENTITY_KINDS.location.kinds).toBe(LOCATION_KINDS);
    expect(ENTITY_KINDS.person.kinds).toBe(PERSON_KINDS);
    expect(ENTITY_KINDS.faction.kinds).toBe(FACTION_KINDS);
    expect(ENTITY_KINDS.item.kinds).toBe(ITEM_KINDS);
  });

  it('knows a path segment it lists from one it does not', () => {
    expect(isEntityKind('person')).toBe(true);
    expect(isEntityKind('toString')).toBe(false);
    expect(isEntityKind('faction')).toBe(true);
    expect(isEntityKind('scene')).toBe(false);
  });
});
