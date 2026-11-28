// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM, so no jsdom to load (which, read from an NFS store, can miss Vitest's worker start).
import { describe, expect, it } from 'vitest';
import { cursorOf, entityOf, pageOf, readCursor, type WorldEntity } from './worldEntities';

const at = (iso: string) => new Date(iso);
const row = (id: string, updated: string, deleted: string | null = null) => ({
  id,
  name: `Name ${id}`,
  description: `Text   of\n${id}`,
  updatedAt: at(updated),
  deletedAt: deleted === null ? null : at(deleted),
  campaignId: 'w1' as string | null,
  settingId: null as string | null,
  canonLevel: null as string | null,
  aliases: null as string | null,
  keywords: null as string | null,
  lore: null as string | null,
  provenance: 'homebrew',
  source: null as string | null,
  pictureUrl: null as string | null,
});

describe('entityOf', () => {
  it('gives the sync shape: kind, summary from the description, tombstones', () => {
    expect(entityOf('location', row('l1', '2026-11-20T12:00:00Z'))).toEqual({
      id: 'l1',
      kind: 'location',
      name: 'Name l1',
      aliases: [],
      summary: 'Text of l1',
      picture: null,
      updated_at: '2026-11-20T12:00:00.000Z',
      deleted: false,
      setting_id: null,
      canon: false,
      canon_level: null,
      keywords: [],
      voice: null,
      tts_voice: null,
      person_kind: null,
      unnamed_as: null,
      gender: null,
      lore: null,
      provenance: 'homebrew',
      source: null,
      gm_only: false,
      tags: [],
      relationships: null,
      routine: null,
      motivations: null,
      invariants: null,
      location_id: null,
      parent_id: null,
    });
    expect(entityOf('item', row('i1', '2026-11-20T13:00:00Z', '2026-11-20T13:00:00Z')).deleted).toBe(true);
  });

  it('carries aliases and keywords, and a voice for a person only (S4c)', () => {
    const voice = '{"personality":"Gruff","speech":"","first_message":"","examples":[]}';
    const holst = entityOf('person', { ...row('p1', '2026-11-20T12:00:00Z'), aliases: '["Old Holst"]', keywords: '["stable"]', voice });
    expect([holst.aliases, holst.keywords, holst.voice?.personality]).toEqual([['Old Holst'], ['stable'], 'Gruff']);
    expect(entityOf('location', { ...row('l1', '2026-11-20T12:00:00Z'), voice }).voice).toBeNull();
    // A person's own kind, for telling a PC from an NPC; none for other kinds.
    expect(entityOf('person', { ...row('p2', '2026-11-20T12:00:00Z'), kind: 'pc' }).person_kind).toBe('pc');
    expect(entityOf('location', { ...row('l2', '2026-11-20T12:00:00Z'), kind: 'region' }).person_kind).toBeNull();
  });

  it("carries a person's invariants, the lines they never cross; none for other kinds", () => {
    const invariants = '["Never harms a child","Never breaks a sworn oath"]';
    expect(entityOf('person', { ...row('p7', '2026-11-20T12:00:00Z'), invariants }).invariants).toEqual(['Never harms a child', 'Never breaks a sworn oath']);
    expect(entityOf('person', row('p8', '2026-11-20T12:00:00Z')).invariants).toEqual([]);
    expect(entityOf('location', { ...row('l5', '2026-11-20T12:00:00Z'), invariants }).invariants).toBeNull();
  });

  it('reads a person by their own unnamed_as, else a generic one; none for other kinds', () => {
    expect(entityOf('person', { ...row('p3', '2026-11-20T12:00:00Z'), unnamedAs: 'the hooded woman' }).unnamed_as).toBe('the hooded woman');
    // The route adds species and Role a page at a time; here, gender alone.
    expect(entityOf('person', { ...row('p4', '2026-11-20T12:00:00Z'), gender: 'female' }).unnamed_as).toBe('a woman');
    // Their gender as authored, for pronouns (operator, 2026-11-25: "Need pronoun enforcement").
    expect(entityOf('person', { ...row('p6', '2026-11-20T12:00:00Z'), gender: 'female' }).gender).toBe('female');
    expect(entityOf('location', { ...row('l4', '2026-11-20T12:00:00Z'), gender: 'female' }).gender).toBeNull();
    expect(entityOf('person', { ...row('p5', '2026-11-20T12:00:00Z'), unnamedAs: '' }).unnamed_as).toBe('a stranger');
    expect(entityOf('location', { ...row('l3', '2026-11-20T12:00:00Z'), unnamedAs: 'a place' }).unnamed_as).toBeNull();
  });

  it('marks a setting’s record with no campaign as canon (S6)', () => {
    const canon = entityOf('location', { ...row('t1', '2026-11-20T12:00:00Z'), campaignId: null, settingId: 's1', canonLevel: 'common' });
    expect([canon.canon, canon.setting_id, canon.canon_level]).toEqual([true, 's1', 'common']);
    const local = entityOf('location', { ...row('h1', '2026-11-20T12:00:00Z'), settingId: 's1' });
    expect(local.canon).toBe(false);
  });
});

describe('cursors', () => {
  it('round-trip, and refuse what is not one', () => {
    const entity = { updated_at: '2026-11-20T12:00:00.000Z', id: 'p1' };
    expect(readCursor(cursorOf(entity))).toEqual(entity);
    expect(readCursor('not-a-cursor')).toBeNull();
  });
});

describe('pageOf', () => {
  const entities: WorldEntity[] = [
    entityOf('person', row('b', '2026-11-20T12:00:00Z')),
    entityOf('location', row('a', '2026-11-20T12:00:00Z')),
    entityOf('item', row('c', '2026-11-20T11:00:00Z', '2026-11-20T11:00:00Z')),
  ];

  it('orders by updated_at then id, and pages with a cursor until there is none', () => {
    const first = pageOf(entities, null, 2);
    expect(first.world_entities.map((one) => one.id)).toEqual(['c', 'a']);
    expect(first.next).not.toBeNull();
    const second = pageOf(entities, readCursor(first.next ?? ''), 2);
    expect(second.world_entities.map((one) => one.id)).toEqual(['b']);
    expect(second.next).toBeNull();
  });
});
