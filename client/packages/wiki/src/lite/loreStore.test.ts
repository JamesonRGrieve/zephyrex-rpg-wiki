// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import Database from 'better-sqlite3';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import * as sqliteVec from 'sqlite-vec';
import { afterAll, describe, expect, it } from 'vitest';
import { wordSimilarity } from '../lib/trigram';
import {
  DIMENSION,
  firstPassages,
  forgetRecords,
  indexedVersions,
  indexRecords,
  type LoreStore,
  namesInScope,
  openLoreStore,
  type Scope,
  storeEmbeddings,
  textRanked,
  vectorRanked,
  waiting,
} from './loreStore';

const dir = mkdtempSync(join(tmpdir(), 'lore-'));
afterAll(() => rmSync(dir, { recursive: true, force: true }));

const ENTRY = JSON.stringify([
  { type: 'p', children: [{ text: 'Keeps the Rusty Anchor.' }] },
  { type: 'h2', children: [{ text: 'Motive' }] },
  { type: 'p', children: [{ text: 'Pay the Guild before winter comes.' }] },
]);

function store(): LoreStore {
  const opened = openLoreStore(join(dir, `${Math.random()}.lore`), Database, sqliteVec.load);
  indexRecords(opened, 'person', [{ id: 'tam', name: 'Old Tam', entry: ENTRY, campaignId: 'c1', version: 'v1' }]);
  indexRecords(opened, 'faction', [{ id: 'guild', name: 'The Coin Guild', description: 'Lends at winter rates.', campaignId: 'c1', version: 'v1' }]);
  indexRecords(opened, 'item', [
    { id: 'lantern', name: 'Storm Lantern', description: 'Burns through any winter gale.', settingId: 'st', version: 'v1' },
    { id: 'far', name: 'Far Lantern', description: 'A winter lamp of another world.', settingId: 'other', version: 'v1' },
    { id: 'rt', name: 'Void Lantern', description: 'Winter in the void.', settingId: 'st', gameSystemId: 'rt', version: 'v1' },
  ]);
  indexRecords(opened, 'person', [{ id: 'sal', name: 'Sibling Sal', description: 'Hates winter and guilds.', campaignId: 'c2', version: 'v1' }]);
  return opened;
}

const SCOPE: Scope = { owners: ['c1', 's1'], settingId: 'st', gameSystemId: null };

describe('lite lore store (better-sqlite3 + sqlite-vec)', () => {
  it('loads sqlite-vec and keeps passages in the campaign scope', () => {
    const lore = store();
    expect(lore.vectorProblem).toBeNull();
    const ranked = textRanked(lore, SCOPE, ['winter', 'guild']);
    const records = new Set(
      (lore.db.prepare(`SELECT target_entity_id FROM lore_chunks WHERE id IN (${ranked.map(() => '?').join(',')})`).all(...ranked) as { target_entity_id: string }[]).map(
        (row) => row.target_entity_id,
      ),
    );
    // The campaign's own and its setting's canon of no system; never the sibling's, another setting's or RT's.
    expect(records).toEqual(new Set(['tam', 'guild', 'lantern']));
    expect([...firstPassages(lore, SCOPE, ['tam', 'sal']).keys()]).toEqual(['tam']);
    expect(textRanked(lore, { ...SCOPE, kinds: ['faction'] }, ['winter']).length).toBe(1);
  });

  it('re-cuts a changed record and forgets a gone one', () => {
    const lore = store();
    indexRecords(lore, 'person', [{ id: 'tam', name: 'Old Tam', description: 'Sold the inn and sailed south.', campaignId: 'c1', version: 'v2' }]);
    expect(indexedVersions(lore, 'person').get('tam')).toBe('v2');
    expect(namesInScope(lore, SCOPE).filter((row) => row.name === 'Old Tam')).toHaveLength(1);
    expect(textRanked(lore, SCOPE, ['winter']).length).toBe(2);
    forgetRecords(lore, ['guild']);
    expect(textRanked(lore, SCOPE, ['winter'])).toHaveLength(1);
    expect(indexedVersions(lore, 'faction').size).toBe(0);
  });

  it('ranks embedded passages by cosine, holding the width', () => {
    const lore = store();
    const axis = (index: number): number[] => Array.from({ length: DIMENSION }, (_unused, at) => (at === index ? 1 : 0));
    const rows = waiting(lore, 100);
    storeEmbeddings(lore, 'test', rows.map((row, index) => ({ id: row.id, vector: axis(index) })));
    expect(waiting(lore, 100)).toHaveLength(0);
    const target = rows.findIndex((row) => row.name === 'Storm Lantern');
    const [first] = vectorRanked(lore, SCOPE, axis(target));
    expect(first).toBe(rows[target]!.id);
    // Out of scope never comes back, however near.
    const far = rows.findIndex((row) => row.name === 'Far Lantern');
    expect(vectorRanked(lore, SCOPE, axis(far))).not.toContain(rows[far]!.id);
    expect(() => storeEmbeddings(lore, 'test', [{ id: rows[0]!.id, vector: [1, 2, 3] }])).toThrow(/768/);
  });

  it("measures word similarity as pg_trgm does, roughly", () => {
    expect(wordSimilarity('Storm Lantern', 'she lights a storm lantern')).toBe(1);
    expect(wordSimilarity('Storm Lantern', 'a stormy lanterns glow')).toBeGreaterThan(0.5);
    expect(wordSimilarity('Old Tam', 'the guild calls')).toBeLessThan(0.3);
  });
});
