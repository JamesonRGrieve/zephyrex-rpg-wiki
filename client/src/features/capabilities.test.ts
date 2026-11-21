// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import { LITE_EXTENSIONS } from '~/app/api/v1/extension/route.lite';
import { capabilitiesOf } from './capabilities';

describe('capabilitiesOf', () => {
  it('turns on what lite serves, and no accounts', () => {
    const names = new Set(LITE_EXTENSIONS.map((extension) => extension.name));
    expect(capabilitiesOf(names, true)).toEqual({
      loaded: true,
      worlds: true,
      places: true,
      people: true,
      factions: true,
      items: true,
      journals: true,
      hooks: true,
      taxonomy: true,
      relations: true,
      posts: true,
      // Lite lists neither until its record_metadata routes land (the next prebuilt set).
      properties: false,
      kits: false,
      accounts: false,
    });
  });

  it('turns everything off before the answer arrives', () => {
    expect(capabilitiesOf(new Set(), false)).toEqual({
      loaded: false,
      worlds: false,
      places: false,
      people: false,
      factions: false,
      items: false,
      journals: false,
      hooks: false,
      taxonomy: false,
      relations: false,
      posts: false,
      properties: false,
      kits: false,
      accounts: false,
    });
  });

  it('turns properties on with metadata, and kits with world_properties as well', () => {
    expect(capabilitiesOf(new Set(['metadata']), true)).toMatchObject({ properties: true, kits: false });
    expect(capabilitiesOf(new Set(['metadata', 'world_properties']), true)).toMatchObject({ properties: true, kits: true });
  });

  it('turns accounts on when the hosted server lists auth_session', () => {
    expect(capabilitiesOf(new Set(['auth_session', 'rpg_core']), true).accounts).toBe(true);
  });
});
