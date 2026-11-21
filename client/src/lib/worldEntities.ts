// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A world's entities changed since a time (rpg-ai A15: lorebooks kept in sync with the wiki), the
 * same answer as the server's rpg_core world_entities: each place, person, faction and item as
 * {id, kind, name, aliases, summary, picture, updated_at, deleted}, paged by (updated_at, id) with an opaque
 * cursor. Deleted ones are tombstones. The paging is pure, here; the lite route reads the rows.
 */
import { summary } from '~/lib/summary';

export const WORLD_ENTITY_KINDS = ['location', 'person', 'faction', 'item', 'journal'] as const;
export type WorldEntityKind = (typeof WORLD_ENTITY_KINDS)[number];

export interface EntityRow {
  id: string;
  name: string;
  description: string | null;
  updatedAt: Date;
  deletedAt: Date | null;
  campaignId: string | null;
  settingId: string | null;
  canonLevel: string | null;
}

export interface WorldEntity {
  id: string;
  kind: WorldEntityKind;
  name: string;
  aliases: string[];
  summary: string;
  /** A picture the caller can load (rpg-ai A31); null until the wiki has media (slice S2c). */
  picture: string | null;
  updated_at: string;
  deleted: boolean;
  setting_id: string | null;
  /** Canon (S6): a setting's record with no campaign, which anyone in the setting would know. */
  canon: boolean;
  canon_level: string | null;
}

export const DEFAULT_LIMIT = 100;
export const MAX_LIMIT = 500;

/** The cursor after an entity: its (updated_at, id), opaque to the caller. */
export function cursorOf(entity: Pick<WorldEntity, 'updated_at' | 'id'>): string {
  return Buffer.from(`${entity.updated_at}|${entity.id}`, 'utf8').toString('base64url');
}

/** A cursor read back, or null when it isn't one of ours. */
export function readCursor(cursor: string): { updated_at: string; id: string } | null {
  const text = Buffer.from(cursor, 'base64url').toString('utf8');
  const bar = text.indexOf('|');
  if (bar < 1 || bar === text.length - 1 || Number.isNaN(Date.parse(text.slice(0, bar)))) return null;
  return { updated_at: text.slice(0, bar), id: text.slice(bar + 1) };
}

/** One row as the entity a sync reads. */
export function entityOf(kind: WorldEntityKind, row: EntityRow): WorldEntity {
  return {
    id: row.id,
    kind,
    name: row.name,
    aliases: [],
    summary: summary(row.description),
    picture: null,
    updated_at: row.updatedAt.toISOString(),
    deleted: row.deletedAt !== null,
    setting_id: row.settingId,
    canon: row.campaignId === null && row.settingId !== null,
    canon_level: row.canonLevel,
  };
}

const order = (a: WorldEntity, b: WorldEntity): number =>
  a.updated_at === b.updated_at ? (a.id < b.id ? -1 : a.id > b.id ? 1 : 0) : a.updated_at < b.updated_at ? -1 : 1;

/** One page of entities after the cursor, in (updated_at, id) order, and the cursor for the next. */
export function pageOf(
  entities: readonly WorldEntity[],
  after: { updated_at: string; id: string } | null,
  limit: number,
): { world_entities: WorldEntity[]; next: string | null } {
  const sorted = [...entities].sort(order);
  const rest = after === null ? sorted : sorted.filter((one) => order(one, { ...one, ...after }) > 0);
  const page = rest.slice(0, limit);
  const last = page.at(-1);
  return { world_entities: page, next: rest.length > limit && last !== undefined ? cursorOf(last) : null };
}
