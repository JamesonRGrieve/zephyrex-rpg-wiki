// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * GET /v1/world_entity?campaign_id=[&include_setting=true] or ?setting_id= (a setting's canon, S6),
 * &since=&kinds=&after=&limit= — a world's places, people,
 * factions, items and journals changed since a time, tombstones included (rpg-ai A15), as the server's rpg_core
 * answers it. Lite has one owner, so "under the caller's access" is the owner's own records.
 */
import { apiErrorResponse, localOwner, recordError, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { prisma } from '~/lib/prisma';
import {
  DEFAULT_LIMIT,
  type EntityRow,
  entityOf,
  MAX_LIMIT,
  pageOf,
  readCursor,
  WORLD_ENTITY_KINDS,
  type WorldEntityKind,
} from '~/lib/worldEntities';
import { seenBy } from '~/lib/worldRecords';

const SELECT = {
  id: true,
  name: true,
  description: true,
  updatedAt: true,
  deletedAt: true,
  campaignId: true,
  settingId: true,
  canonLevel: true,
} as const;

function rowsOf(kind: WorldEntityKind, where: object): Promise<EntityRow[]> {
  switch (kind) {
    case 'location':
      return prisma.location.findMany({ where, select: SELECT });
    case 'person':
      return prisma.person.findMany({ where, select: SELECT });
    case 'faction':
      return prisma.faction.findMany({ where, select: SELECT });
    case 'item':
      return prisma.item.findMany({ where, select: SELECT });
    case 'journal':
      return prisma.journal.findMany({ where, select: SELECT });
  }
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const query = request.nextUrl.searchParams;
    const campaignId = query.get('campaign_id') || null;
    const settingId = query.get('setting_id') || null;
    if ((campaignId === null) === (settingId === null)) throw validationError('Name a campaign_id or a setting_id', 'campaign_id');
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
    return NextResponse.json(pageOf(rows.flat(), after, limit));
  } catch (error) {
    return apiErrorResponse(error);
  }
}
