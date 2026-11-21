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
});

describe('entityOf', () => {
  it('gives the sync shape: kind, summary from the description, no aliases yet, tombstones', () => {
    expect(entityOf('location', row('l1', '2026-11-20T12:00:00Z'))).toEqual({
      id: 'l1',
      kind: 'location',
      name: 'Name l1',
      aliases: [],
      summary: 'Text of l1',
      picture: null,
      updated_at: '2026-11-20T12:00:00.000Z',
      deleted: false,
    });
    expect(entityOf('item', row('i1', '2026-11-20T13:00:00Z', '2026-11-20T13:00:00Z')).deleted).toBe(true);
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
