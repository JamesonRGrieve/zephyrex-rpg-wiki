// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A setting's pregenerated player characters, as the server's rpg_core answers them (operator,
 * 2026-11-21: setting-wide characters to pick from, a couple per class): its canon persons of kind
 * pc tagged Pregen. GET /v1/setting/{id}/pregen lists them; a start copies the picked ones in
 * (scenarios.ts). Lite has one owner.
 */
import { apiErrorResponse, localOwner, notFound, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { LIMITS } from '../contract';
import { prisma } from './db';

type Context = { params: Promise<Record<string, string>> };
type Client = Pick<typeof prisma, 'taxon' | 'entityTaxon' | 'person'>;

const PREGEN = 'pregen';

/** The summary of a plain text, at most the contract's summary length (wiki_shared.Summary's rule). */
function summarised(text: string): string {
  const flat = text.replace(/\s+/g, ' ').trim();
  if (flat.length <= LIMITS.summary_characters) return flat;
  const room = flat.slice(0, LIMITS.summary_characters - 1);
  const cut = room.lastIndexOf(' ');
  return `${(cut > 0 ? room.slice(0, cut) : room).trimEnd()}…`;
}

/** The setting's canon pcs tagged Pregen, and each tagged record's tag names. */
async function pregenIds(db: Client, ownerId: string, settingId: string): Promise<{ tagged: Set<string>; names: Map<string, string[]> }> {
  const taxa = await db.taxon.findMany({ where: { createdById: ownerId, settingId, deletedAt: null }, select: { id: true, name: true } });
  const byId = new Map(taxa.map((taxon) => [taxon.id, taxon.name]));
  const pregen = taxa.filter((taxon) => taxon.name.trim().toLocaleLowerCase() === PREGEN).map((taxon) => taxon.id);
  const tagged = new Set(
    (await db.entityTaxon.findMany({ where: { taxonId: { in: pregen }, targetEntityType: 'person' }, select: { targetEntityId: true } })).map((row) => row.targetEntityId),
  );
  const names = new Map<string, string[]>();
  for (const row of await db.entityTaxon.findMany({ where: { targetEntityId: { in: [...tagged] } }, select: { targetEntityId: true, taxonId: true } })) {
    const name = byId.get(row.taxonId);
    if (name !== undefined) names.set(row.targetEntityId, [...(names.get(row.targetEntityId) ?? []), name]);
  }
  return { tagged, names };
}

/** The picked pregens' person rows, each one of the setting's pregens (422 otherwise). */
export async function pregenRows<T extends Client>(db: T, ownerId: string, settingId: string | null, ids: readonly string[]): Promise<Record<string, unknown>[]> {
  if (ids.length === 0) return [];
  if (!settingId) throw validationError('This scenario has no setting, so no pregens to pick from', 'pregens');
  const { tagged } = await pregenIds(db, ownerId, settingId);
  const rows = await db.person.findMany({ where: { id: { in: [...ids] }, createdById: ownerId, settingId, campaignId: null, deletedAt: null } });
  for (const id of new Set(ids)) {
    if (!tagged.has(id) || !rows.some((row) => row.id === id)) throw validationError(`${id} isn't one of this setting's pregens`, 'pregens');
  }
  return rows as unknown as Record<string, unknown>[];
}

/** GET /v1/setting/{id}/pregen → {pregens: [{id, name, summary, picture_url, tags, source}]}. */
export async function settingPregensGet(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const settingId = (await context.params).id ?? '';
    const setting = await prisma.setting.findFirst({ where: { id: settingId }, select: { id: true } });
    if (setting === null) throw notFound('SettingModel');
    const { tagged, names } = await pregenIds(prisma, owner.id, settingId);
    const people = await prisma.person.findMany({
      where: { id: { in: [...tagged] }, createdById: owner.id, settingId, campaignId: null, kind: 'pc', deletedAt: null },
      select: { id: true, name: true, description: true, pictureUrl: true, source: true },
    });
    const pregens = people
      .sort((a, b) => a.name.toLocaleLowerCase().localeCompare(b.name.toLocaleLowerCase()))
      .map((row) => ({
        id: row.id,
        name: row.name,
        summary: summarised(row.description.split('\n').find((line) => line.trim() !== '') ?? ''),
        picture_url: row.pictureUrl,
        tags: [...(names.get(row.id) ?? [])].sort((a, b) => Number(a.toLocaleLowerCase() !== PREGEN) - Number(b.toLocaleLowerCase() !== PREGEN) || a.toLocaleLowerCase().localeCompare(b.toLocaleLowerCase())),
        source: row.source,
      }));
    return NextResponse.json({ pregens });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
