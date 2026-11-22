// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Lite's lore index (the twin of rpg_core's lore_chunks; operator, 2026-11-22: "Install
 * better-sqlite3 + sqlite-vec"). A better-sqlite3 database of its own beside the app's (the app's
 * file + ".lore"; Prisma would read tables it doesn't know as drift), with sqlite-vec loaded:
 *
 * - lore_chunks: each record's passages (lib/loreIndex chunkEntry), with its scope;
 * - lore_fts: FTS5 over name and text (diacritics removed), the full-text rank;
 * - lore_vec: a vec0 table of 768-wide cosine embeddings (nomic-embed-text-v1.5), the vector rank;
 * - lore_records: which version of each record its passages are of, so a search brings only the
 *   changed records up to date (lite has no write hooks), and drops the gone.
 *
 * It can always be rebuilt from the records, so it never holds anything of its own.
 */
import type BetterSqlite3 from 'better-sqlite3';
import { randomUUID } from 'node:crypto';
import { chunkEntry, tokens } from '../lib/loreIndex';

export const DIMENSION = 768;
export const RANK_DEPTH = 60;

export interface LoreStore {
  db: BetterSqlite3.Database;
  /** Why vectors are off (sqlite-vec didn't load), or null when they're on. */
  vectorProblem: string | null;
}

export interface LoreRecord {
  id: string;
  name: string;
  description?: string | null;
  entry?: string | null;
  campaignId?: string | null;
  settingId?: string | null;
  gameSystemId?: string | null;
  kind?: string | null;
  source?: string | null;
}

export interface Scope {
  owners: string[];
  settingId: string | null;
  gameSystemId: string | null;
  kinds?: readonly string[];
}

let file: string | undefined;
let opened: Promise<LoreStore> | undefined;

/** The lore file (tests, or an app keeping it elsewhere); default: DATABASE_URL's file + ".lore". */
export function bindLoreFile(given: string): void {
  file = given;
  opened = undefined;
}

function loreFile(): string {
  if (file !== undefined) return file;
  return `${(process.env.DATABASE_URL ?? 'file:./rpg_wiki.db').replace(/^file:/, '')}.lore`;
}

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS lore_chunks (
    id TEXT PRIMARY KEY, target_entity_type TEXT NOT NULL, target_entity_id TEXT NOT NULL, name TEXT NOT NULL,
    campaign_id TEXT, setting_id TEXT, game_system_id TEXT, kind TEXT, source TEXT, page INTEGER,
    position INTEGER NOT NULL, path TEXT NOT NULL, text TEXT NOT NULL, tokens INTEGER NOT NULL,
    embedded_model TEXT, embedded_at TEXT, created_at TEXT NOT NULL)`,
  'CREATE INDEX IF NOT EXISTS ix_lore_chunks_record ON lore_chunks (target_entity_id)',
  'CREATE INDEX IF NOT EXISTS ix_lore_chunks_waiting ON lore_chunks (embedded_at, created_at)',
  "CREATE VIRTUAL TABLE IF NOT EXISTS lore_fts USING fts5(chunk_id UNINDEXED, name, text, tokenize = 'unicode61 remove_diacritics 2')",
  'CREATE TABLE IF NOT EXISTS lore_records (record_id TEXT PRIMARY KEY, kind TEXT NOT NULL, version TEXT NOT NULL)',
];

export function openLoreStore(path: string, Database: typeof BetterSqlite3, loadVec?: (db: BetterSqlite3.Database) => void): LoreStore {
  const db = new Database(path);
  db.pragma('journal_mode = WAL');
  let vectorProblem: string | null = null;
  try {
    if (loadVec === undefined) throw new Error('sqlite-vec is not installed');
    loadVec(db);
  } catch (error) {
    vectorProblem = `sqlite-vec could not load (${error instanceof Error ? error.message : String(error)})`;
  }
  for (const statement of SCHEMA) db.exec(statement);
  if (vectorProblem === null)
    db.exec(`CREATE VIRTUAL TABLE IF NOT EXISTS lore_vec USING vec0(chunk_id TEXT PRIMARY KEY, embedding float[${DIMENSION}] distance_metric=cosine)`);
  return { db, vectorProblem };
}

/** The app's lore store, opened once (better-sqlite3 and sqlite-vec loaded only when it's asked for). */
export function loreStore(): Promise<LoreStore> {
  opened ??= (async () => {
    const { default: Database } = await import('better-sqlite3');
    let loadVec: ((db: BetterSqlite3.Database) => void) | undefined;
    try {
      loadVec = (await import('sqlite-vec')).load;
    } catch {
      loadVec = undefined;
    }
    return openLoreStore(loreFile(), Database, loadVec);
  })();
  return opened;
}

function dropChunks(store: LoreStore, recordIds: readonly string[]): void {
  const ids = store.db.prepare('SELECT id FROM lore_chunks WHERE target_entity_id = ?');
  const fts = store.db.prepare('DELETE FROM lore_fts WHERE chunk_id = ?');
  const vec = store.vectorProblem === null ? store.db.prepare('DELETE FROM lore_vec WHERE chunk_id = ?') : null;
  const chunks = store.db.prepare('DELETE FROM lore_chunks WHERE target_entity_id = ?');
  for (const recordId of recordIds) {
    for (const { id } of ids.all(recordId) as { id: string }[]) {
      fts.run(id);
      vec?.run(id);
    }
    chunks.run(recordId);
  }
}

/** A record's passages: its entry's, else its description, else its name alone (as the server). */
export function passagesOf(record: LoreRecord): { path: string[]; text: string }[] {
  const found = chunkEntry(record.name, record.entry ?? null);
  return found.length > 0 ? found : [{ path: [record.name], text: (record.description ?? '').trim() || record.name }];
}

/** These records' passages, replacing any they had; ``version`` is what each is now (its updatedAt). */
export function indexRecords(store: LoreStore, kind: string, records: readonly (LoreRecord & { version: string })[]): number {
  let written = 0;
  const insert = store.db.prepare(
    `INSERT INTO lore_chunks (id, target_entity_type, target_entity_id, name, campaign_id, setting_id, game_system_id, kind, source, position, path, text, tokens, created_at)
     VALUES (@id, @type, @record, @name, @campaign, @setting, @system, @kind, @source, @position, @path, @text, @tokens, @at)`,
  );
  const fts = store.db.prepare('INSERT INTO lore_fts (chunk_id, name, text) VALUES (?, ?, ?)');
  const seen = store.db.prepare('INSERT INTO lore_records (record_id, kind, version) VALUES (?, ?, ?) ON CONFLICT (record_id) DO UPDATE SET version = excluded.version, kind = excluded.kind');
  store.db.transaction(() => {
    dropChunks(store, records.map((record) => record.id));
    const at = new Date().toISOString();
    for (const record of records) {
      passagesOf(record).forEach((passage, position) => {
        const id = randomUUID();
        insert.run({
          id,
          type: kind,
          record: record.id,
          name: record.name,
          campaign: record.campaignId ?? null,
          setting: record.settingId ?? null,
          system: record.gameSystemId ?? null,
          kind: record.kind ?? null,
          source: record.source ?? null,
          position,
          path: JSON.stringify(passage.path),
          text: passage.text,
          tokens: tokens(passage.text),
          at,
        });
        fts.run(id, record.name, passage.text);
        written += 1;
      });
      seen.run(record.id, kind, record.version);
    }
  })();
  return written;
}

/** The records' passages gone (deleted, made templates, or no longer there). */
export function forgetRecords(store: LoreStore, recordIds: readonly string[]): void {
  const forget = store.db.prepare('DELETE FROM lore_records WHERE record_id = ?');
  store.db.transaction(() => {
    dropChunks(store, recordIds);
    for (const id of recordIds) forget.run(id);
  })();
}

/** Which version of each record of ``kind`` the index holds. */
export function indexedVersions(store: LoreStore, kind: string): Map<string, string> {
  const rows = store.db.prepare('SELECT record_id, version FROM lore_records WHERE kind = ?').all(kind) as { record_id: string; version: string }[];
  return new Map(rows.map((row) => [row.record_id, row.version]));
}

function scopeSql(scope: Scope, alias = ''): { sql: string; params: unknown[] } {
  const column = (name: string): string => `${alias}${name}`;
  const parts = [`${column('campaign_id')} IN (${scope.owners.map(() => '?').join(', ')})`];
  const params: unknown[] = [...scope.owners];
  if (scope.settingId !== null) {
    parts.push(
      `(${column('campaign_id')} IS NULL AND ${column('setting_id')} = ? AND (${column('game_system_id')} IS NULL${scope.gameSystemId === null ? '' : ` OR ${column('game_system_id')} = ?`}))`,
    );
    params.push(scope.settingId, ...(scope.gameSystemId === null ? [] : [scope.gameSystemId]));
  }
  let sql = `(${parts.join(' OR ')})`;
  if (scope.kinds !== undefined && scope.kinds.length > 0) {
    sql += ` AND ${column('target_entity_type')} IN (${scope.kinds.map(() => '?').join(', ')})`;
    params.push(...scope.kinds);
  }
  return { sql, params };
}

/** The records' first passages in scope, by record id. */
export function firstPassages(store: LoreStore, scope: Scope, recordIds: readonly string[]): Map<string, string> {
  if (recordIds.length === 0) return new Map();
  const where = scopeSql(scope);
  const rows = store.db
    .prepare(`SELECT id, target_entity_id FROM lore_chunks WHERE position = 0 AND ${where.sql} AND target_entity_id IN (${recordIds.map(() => '?').join(', ')})`)
    .all(...where.params, ...recordIds) as { id: string; target_entity_id: string }[];
  return new Map(rows.map((row) => [row.target_entity_id, row.id]));
}

/** FTS5's best passages in scope for the text (any of its words, bm25). */
export function textRanked(store: LoreStore, scope: Scope, words: readonly string[]): string[] {
  if (words.length === 0) return [];
  const where = scopeSql(scope, 'c.');
  const match = words.map((word) => `"${word.replaceAll('"', '""')}"`).join(' OR ');
  const rows = store.db
    .prepare(`SELECT c.id FROM lore_fts f JOIN lore_chunks c ON c.id = f.chunk_id WHERE lore_fts MATCH ? AND ${where.sql} ORDER BY bm25(lore_fts), c.id LIMIT ${RANK_DEPTH}`)
    .all(match, ...where.params) as { id: string }[];
  return rows.map((row) => row.id);
}

/** Each record's first passage in scope with its name (for the trigram rank). */
export function namesInScope(store: LoreStore, scope: Scope): { id: string; name: string }[] {
  const where = scopeSql(scope);
  return store.db.prepare(`SELECT id, name FROM lore_chunks WHERE position = 0 AND ${where.sql}`).all(...where.params) as { id: string; name: string }[];
}

/** The nearest embedded passages in scope (cosine), from a KNN over all, kept to the scope. */
export function vectorRanked(store: LoreStore, scope: Scope, vector: readonly number[]): string[] {
  if (store.vectorProblem !== null) return [];
  const where = scopeSql(scope);
  const inScope = new Set((store.db.prepare(`SELECT id FROM lore_chunks WHERE embedded_at IS NOT NULL AND ${where.sql}`).all(...where.params) as { id: string }[]).map((row) => row.id));
  if (inScope.size === 0) return [];
  const rows = store.db
    .prepare('SELECT chunk_id FROM lore_vec WHERE embedding MATCH ? AND k = ? ORDER BY distance')
    .all(JSON.stringify(checkedVector(vector)), Math.min(4096, Math.max(RANK_DEPTH * 5, inScope.size))) as { chunk_id: string }[];
  return rows.map((row) => row.chunk_id).filter((id) => inScope.has(id)).slice(0, RANK_DEPTH);
}

export function checkedVector(vector: readonly number[]): readonly number[] {
  if (vector.length !== DIMENSION) throw new Error(`The embedder answered ${vector.length} dimensions; the lore index holds ${DIMENSION} (nomic-embed-text-v1.5)`);
  return vector;
}

/** Passages not yet embedded, oldest first. */
export function waiting(store: LoreStore, limit: number): { id: string; name: string; text: string }[] {
  return store.db.prepare('SELECT id, name, text FROM lore_chunks WHERE embedded_at IS NULL ORDER BY created_at, id LIMIT ?').all(limit) as { id: string; name: string; text: string }[];
}

export function storeEmbeddings(store: LoreStore, model: string, rows: readonly { id: string; vector: readonly number[] }[]): void {
  const vec = store.db.prepare('INSERT OR REPLACE INTO lore_vec (chunk_id, embedding) VALUES (?, ?)');
  const done = store.db.prepare('UPDATE lore_chunks SET embedded_model = ?, embedded_at = ? WHERE id = ?');
  const at = new Date().toISOString();
  store.db.transaction(() => {
    for (const row of rows) {
      vec.run(row.id, JSON.stringify(checkedVector(row.vector)));
      done.run(model, at, row.id);
    }
  })();
}

export interface ChunkRow {
  id: string;
  target_entity_type: string;
  target_entity_id: string;
  name: string;
  path: string;
  text: string;
  tokens: number;
  source: string | null;
  page: number | null;
}

export function chunksById(store: LoreStore, ids: readonly string[]): Map<string, ChunkRow> {
  if (ids.length === 0) return new Map();
  const rows = store.db
    .prepare(`SELECT id, target_entity_type, target_entity_id, name, path, text, tokens, source, page FROM lore_chunks WHERE id IN (${ids.map(() => '?').join(', ')})`)
    .all(...ids) as ChunkRow[];
  return new Map(rows.map((row) => [row.id, row]));
}
