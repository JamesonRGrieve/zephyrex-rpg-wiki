// SPDX-License-Identifier: AGPL-3.0-or-later
// Sample worlds, places and people for this folder's tests and stories: one shape, both read it.
import type { Person, Place, World } from '~/features/data/records';

const STAMP = { created_at: '2026-11-20T12:00:00Z', updated_at: '2026-11-20T12:00:00Z' };

export const WORLDS: World[] = [
  { id: 'w1', name: 'The Salt Coast', description: 'Smugglers and storm-gods.', ...STAMP },
  { id: 'w2', name: 'Hollowmere', description: null, ...STAMP },
];

const place = (id: string, name: string, kind: string | null, parent_id: string | null, description = ''): Place => ({
  id,
  name,
  kind,
  parent_id,
  description,
  entry: null,
  campaign_id: 'w1',
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

export const ENTRY = JSON.stringify([
  { type: 'h2', children: [{ text: 'History' }] },
  { type: 'p', children: [{ text: 'Founded by smugglers.' }] },
]);
