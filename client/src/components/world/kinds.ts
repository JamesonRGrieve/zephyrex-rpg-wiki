// SPDX-License-Identifier: AGPL-3.0-or-later
// The record kinds a world's pages list (/w/[world]/[kind]), each with its words and its kinds.
import { LOCATION_KINDS, PERSON_KINDS } from '~/contract';
import type { Capabilities } from '~/features/capabilities';

export const ENTITY_KINDS = {
  location: { what: 'place', plural: 'places', title: 'Places', kinds: LOCATION_KINDS, needs: 'places' },
  person: { what: 'person', plural: 'people', title: 'People', kinds: PERSON_KINDS, needs: 'people' },
} as const satisfies Record<string, { what: string; plural: string; title: string; kinds: readonly string[]; needs: keyof Capabilities }>;

export type EntityKind = keyof typeof ENTITY_KINDS;

export const isEntityKind = (value: string): value is EntityKind => Object.hasOwn(ENTITY_KINDS, value);
