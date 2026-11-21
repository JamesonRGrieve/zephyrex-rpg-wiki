// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * GET /v1/world_entity?campaign_id=[&include_setting=true] or ?setting_id= (a setting's canon, S6),
 * or ?ids=a,b (the named records wherever they are), &since=&kinds=&after=&limit= — a world's places, people,
 * factions, items and journals changed since a time, tombstones included (rpg-ai A15), as the server's rpg_core
 * answers it. Lite has one owner, so "under the caller's access" is the owner's own records.
 */
import { apiErrorResponse, localOwner, recordError, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { prisma } from './db';
import {
  DEFAULT_LIMIT,
  type EntityRow,
  entityOf,
  MAX_LIMIT,
  pageOf,
  readCursor,
  WORLD_ENTITY_KINDS,
  type WorldEntityKind,
} from './worldEntities';
import { seenBy } from './worldRecords';
import { EntityIdsError, entityIds } from '../lib/entityIds';
import { GM_ONLY_PROPERTY } from '../contract';

const SELECT = {
  id: true,
  name: true,
  description: true,
  updatedAt: true,
  deletedAt: true,
  campaignId: true,
  settingId: true,
  canonLevel: true,
  aliases: true,
  keywords: true,
  lore: true,
  provenance: true,
  source: true,
  pictureUrl: true,
} as const;

function rowsOf(kind: WorldEntityKind, where: object): Promise<EntityRow[]> {
  switch (kind) {
    case 'location':
      return prisma.location.findMany({ where, select: { ...SELECT, parentId: true } });
    case 'person':
      return prisma.person.findMany({ where, select: { ...SELECT, voice: true, locationId: true } });
    case 'faction':
      return prisma.faction.findMany({ where, select: { ...SELECT, parentId: true } });
    case 'item':
      return prisma.item.findMany({ where, select: SELECT });
    case 'journal':
      return prisma.journal.findMany({ where, select: SELECT });
  }
}

/** Each record kept to the GM: its private "GM only" property is "true" (one query for the page). */
async function withSecrecy<T extends { id: string; kind: string; gm_only: boolean }>(shown: T[]): Promise<T[]> {
  if (shown.length === 0) return shown;
  const rows = await prisma.recordMetadata.findMany({
    where: { key: GM_ONLY_PROPERTY, targetEntityId: { in: shown.map((entity) => entity.id) } },
    select: { targetEntityType: true, targetEntityId: true, value: true },
  });
  const secret = new Set(rows.filter((row) => (row.value ?? '').trim().toLowerCase() === 'true').map((row) => `${row.targetEntityType}:${row.targetEntityId}`));
  return shown.map((entity) => ({ ...entity, gm_only: secret.has(`${entity.kind}:${entity.id}`) }));
}

/**
 * ?ids=a,b: the named records wherever they are (rpg-ai's sandbox cast), shaped as the sync shapes
 * them, in the order asked. An id that isn't the owner's, a deleted record, a template or an unknown
 * id is simply absent, as on the server; `next` is always none.
 */
async function byId(ownerId: string, text: string): Promise<NextResponse> {
  let ids: string[];
  try {
    ids = entityIds(text.split(','));
  } catch (error) {
    if (error instanceof EntityIdsError) throw validationError(error.message, 'ids');
    throw error;
  }
  const where = { createdById: ownerId, id: { in: ids }, deletedAt: null, OR: [{ isTemplate: null }, { isTemplate: false }] };
  const rows = await Promise.all(WORLD_ENTITY_KINDS.map(async (kind) => (await rowsOf(kind, where)).map((row) => entityOf(kind, row))));
  const order = new Map(ids.map((id, index) => [id, index]));
  const found = rows.flat().sort((one, two) => (order.get(one.id) ?? 0) - (order.get(two.id) ?? 0));
  return NextResponse.json({ world_entities: await withSecrecy(found), next: null });
}

export async function worldEntityGet(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const query = request.nextUrl.searchParams;
    const campaignId = query.get('campaign_id') || null;
    const settingId = query.get('setting_id') || null;
    const idsText = query.get('ids');
    if ([campaignId, settingId, idsText].filter((one) => one !== null).length !== 1)
      throw validationError('Name a campaign_id, a setting_id or ids', 'campaign_id');
    if (idsText !== null) return await byId(owner.id, idsText);
    let canonOf: string | null = settingId;
    if (campaignId !== null) {
      const campaign = await prisma.campaign.findFirst({ where: { id: campaignId, createdById: owner.id }, select: { settingId: true } });
      if (campaign === null) throw recordError(404, 'CampaignModel not found');
      canonOf = query.get('include_setting') === 'true' ? campaign.settingId : null;
    } else if ((await prisma.setting.count({ where: { id: settingId ?? '', ...seenBy(owner.id) } })) === 0) {
      throw recordError(404, 'SettingModel not found');
    }
    const sinceText = query.get('since');
    const since = sinceText === null || sinceText === '' ? null : new Date(sinceText);
    if (since !== null && Number.isNaN(since.getTime())) throw validationError('since is not a date', 'since');
    const kindsText = query.get('kinds');
    const kinds = kindsText === null || kindsText === '' ? [...WORLD_ENTITY_KINDS] : kindsText.split(',');
    const unknown = kinds.filter((kind) => !(WORLD_ENTITY_KINDS as readonly string[]).includes(kind));
    if (unknown.length > 0) throw validationError(`Unknown kinds: ${unknown.join(', ')}`, 'kinds');
    const limitText = query.get('limit');
    const limit = limitText === null || limitText === '' ? DEFAULT_LIMIT : Number(limitText);
    if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT)
      throw validationError(`limit is 1 to ${MAX_LIMIT}`, 'limit');
    const afterText = query.get('after');
    const after = afterText === null || afterText === '' ? null : readCursor(afterText);
    if (afterText !== null && afterText !== '' && after === null) throw validationError('after is not a cursor', 'after');

    // A template (S4b) is copied into campaigns, never a world fact: as the server, it never syncs.
    const changed = { OR: [{ isTemplate: null }, { isTemplate: false }], ...(since === null ? {} : { updatedAt: { gte: since } }) };
    // The campaign's own records, and (asked for, or alone) its setting's canon: no campaign.
    const scopes: object[] = [
      ...(campaignId === null ? [] : [{ createdById: owner.id, campaignId, ...changed }]),
      ...(canonOf === null ? [] : [{ createdById: owner.id, settingId: canonOf, campaignId: null, ...changed }]),
    ];
    const rows = await Promise.all(
      scopes.flatMap((where) =>
        (kinds as WorldEntityKind[]).map(async (kind) => (await rowsOf(kind, where)).map((row) => entityOf(kind, row))),
      ),
    );
    const page = pageOf(rows.flat(), after, limit);
    return NextResponse.json({ ...page, world_entities: await withSecrecy(page.world_entities) });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
