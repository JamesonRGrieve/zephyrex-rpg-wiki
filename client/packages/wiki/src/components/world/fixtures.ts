// SPDX-License-Identifier: AGPL-3.0-or-later
// Sample worlds, places and people for this folder's tests and stories: one shape, both read it.
import type { Faction, Item, Person, Place, World } from '../../features/data/records';

const STAMP = { created_at: '2026-11-20T12:00:00Z', updated_at: '2026-11-20T12:00:00Z' };

export const WORLDS: World[] = [
  { id: 'w1', name: 'The Salt Coast', description: 'Smugglers and storm-gods.', ...STAMP },
  { id: 'w2', name: 'Hollowmere', description: null, provenance: 'official', source: 'The Hollowmere Gazetteer, p. 3', ...STAMP },
];

const place = (id: string, name: string, kind: string | null, parent_id: string | null, description = ''): Place => ({
  id,
  name,
  kind,
  parent_id,
  description,
  entry: null,
  campaign_id: 'w1',
  associated_person_id: null,
  ...STAMP,
});

export const PLACES: Place[] = [
  place('l1', 'The Coast', 'region', null, 'A long grey shore.'),
  place('l2', 'Saltmarsh', 'city', 'l1', 'A port city.'),
  place('l3', 'The Gull', 'building', 'l2', 'An inn with a crooked sign.'),
  place('l4', 'Brine', 'city', 'l1'),
];

export const PEOPLE: Person[] = [
  {
    id: 'p1',
    name: 'Mira',
    kind: 'npc',
    description: 'Keeper of the Gull.',
    entry: null,
    campaign_id: 'w1',
    location_id: 'l3',
    ...STAMP,
  },
];

const faction = (id: string, name: string, kind: string, parent_id: string | null): Faction => ({
  id,
  name,
  kind,
  parent_id,
  description: '',
  entry: null,
  campaign_id: 'w1',
  ...STAMP,
});

export const FACTIONS: Faction[] = [
  faction('f1', 'House Vell', 'family', null),
  faction('f2', 'The Cadet Line', 'family', 'f1'),
  faction('f3', 'Brine Syndicate', 'criminal', null),
];

export const ITEMS: Item[] = [
  {
    id: 'i1',
    name: 'Salt-steel sabre',
    kind: 'weapon',
    description: 'Never rusts.',
    entry: null,
    weight: 1.5,
    base_value: 40,
    stack_size: 1,
    campaign_id: 'w1',
    ...STAMP,
  },
];

export const ENTRY = JSON.stringify([
  { type: 'h2', children: [{ text: 'History' }] },
  { type: 'p', children: [{ text: 'Founded by smugglers.' }] },
]);
