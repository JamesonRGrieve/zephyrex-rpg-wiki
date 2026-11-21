// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import { capabilitiesOf } from './capabilities';

describe('capabilitiesOf', () => {
  it('turns each section on with the extension that serves it', () => {
    const on = capabilitiesOf(new Set(['rpg_core', 'world_spatial', 'genealogy', 'world_social', 'metadata', 'world_properties']), true);
    expect(on).toMatchObject({ loaded: true, worlds: true, places: true, people: true, relations: true, properties: true, kits: true, items: false, posts: false });
  });

  it('turns everything off before the back end has answered', () => {
    expect(Object.values(capabilitiesOf(new Set(['rpg_core']), false)).filter((value) => value === true)).toEqual([true]);
    expect(capabilitiesOf(new Set(), false).loaded).toBe(false);
  });
});
