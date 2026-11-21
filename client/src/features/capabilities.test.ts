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
      posts: true,
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
      posts: false,
      accounts: false,
    });
  });

  it('turns accounts on when the hosted server lists auth_session', () => {
    expect(capabilitiesOf(new Set(['auth_session', 'rpg_core']), true).accounts).toBe(true);
  });
});
