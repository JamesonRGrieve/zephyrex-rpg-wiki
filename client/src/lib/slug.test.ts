// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM. Held to the cases the server is held to (contract/slug-cases.json).
import { describe, expect, it } from 'vitest';
import cases from '../../../contract/slug-cases.json';
import { SEED_SETTINGS } from '~/contract';
import { freeSlug, isSlug, slugify } from './slug';

describe('slugify', () => {
  it.each(cases.derived.map((one) => [one.name, one.slug] as const))('%s → %s', (name, slug) => {
    expect(slugify(name)).toBe(slug);
  });
});

describe('freeSlug', () => {
  it.each(cases.deduplicated.map((one) => [one.taken.join(',') || 'free', one] as const))('%s', (_label, one) => {
    expect(freeSlug(one.slug, (candidate) => one.taken.includes(candidate))).toBe(one.free);
  });

  it('keeps a numbered slug within the length', () => {
    const long = slugify('x'.repeat(100));
    expect(freeSlug(long, (candidate) => candidate === long)).toHaveLength(long.length);
  });
});

describe('isSlug', () => {
  it.each(cases.invalid.map((slug) => [slug] as const))('refuses %j', (slug) => {
    expect(isSlug(slug)).toBe(false);
  });

  it('accepts every seeded slug, each once', () => {
    const slugs = SEED_SETTINGS.map((one) => one.slug);
    expect(slugs.every(isSlug)).toBe(true);
    expect(new Set(slugs).size).toBe(6);
  });
});
