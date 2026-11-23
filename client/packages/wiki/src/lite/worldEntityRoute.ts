// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * GET /v1/world_entity?campaign_id=[&include_setting=true] or ?setting_id= (a setting's canon, S6),
 * or ?ids=a,b (the named records wherever they are), &since=&kinds=&after=&limit= — a world's places, people,
 * factions, items and journals changed since a time, tombstones included (rpg-ai A15), as the server's rpg_core
 * answers it. Lite has one owner, so "under the caller's access" is the owner's own records.
 */
import { apiErrorResponse, localOwner, parseBody, readJsonObject, recordError, validationError } from '@zephyrex/lite';
import { z } from 'zod';
import { ALWAYS, recordKeys, textGrams } from '../lib/worldKeys';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { prisma } from './db';
import { eraExcluded } from './eras';
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
import type { Tie } from './worldEntities';

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
      return prisma.person.findMany({ where, select: { ...SELECT, voice: true, ttsVoice: true, locationId: true, routine: true, motivations: true } });
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
  const secret = await secretsOf(shown.map((entity) => entity.id));
  return shown.map((entity) => ({ ...entity, gm_only: secret.has(`${entity.kind}:${entity.id}`) }));
}

/** The GM-only marks of these records (their private "GM only" property is "true"). */
async function secretsOf(ids: readonly string[]): Promise<Set<string>> {
  if (ids.length === 0) return new Set();
  const rows = await prisma.recordMetadata.findMany({
    where: { key: GM_ONLY_PROPERTY, targetEntityId: { in: [...ids] } },
    select: { targetEntityType: true, targetEntityId: true, value: true },
  });
  return new Set(rows.filter((row) => (row.value ?? '').trim().toLowerCase() === 'true').map((row) => `${row.targetEntityType}:${row.targetEntityId}`));
}

/**
 * Each record's tag names (rpg-ai finds the party by "PC") and each person's ties to other people
 * ({to_id, kind, note}), as the server's; a tie with a GM-only end is left out.
 */
async function withTagsAndTies<T extends { id: string; kind: string; tags: string[]; relationships: Tie[] | null }>(ownerId: string, shown: T[]): Promise<T[]> {
  if (shown.length === 0) return shown;
  const ids = shown.map((entity) => entity.id);
  const links = await prisma.entityTaxon.findMany({ where: { createdById: ownerId, targetEntityId: { in: ids } }, select: { taxonId: true, targetEntityType: true, targetEntityId: true } });
  const taxa = await prisma.taxon.findMany({ where: { id: { in: [...new Set(links.map((link) => link.taxonId))] }, deletedAt: null }, select: { id: true, name: true } });
  const nameOf = new Map(taxa.map((taxon) => [taxon.id, taxon.name]));
  const tagged = new Map<string, Set<string>>();
  for (const link of links) {
    const name = nameOf.get(link.taxonId);
    if (name === undefined) continue;
    const key = `${link.targetEntityType}:${link.targetEntityId}`;
    tagged.set(key, (tagged.get(key) ?? new Set()).add(name));
  }
  const people = shown.filter((entity) => entity.kind === 'person').map((entity) => entity.id);
  const ties = people.length === 0 ? [] : await prisma.relationship.findMany({ where: { createdById: ownerId, personId: { in: people }, targetPersonId: { not: null } } });
  const secret = await secretsOf([...people, ...ties.flatMap((tie) => (tie.targetPersonId === null ? [] : [tie.targetPersonId]))]);
  const byPerson = new Map<string, Tie[]>();
  for (const tie of ties) {
    if (tie.personId === null || tie.targetPersonId === null || secret.has(`person:${tie.personId}`) || secret.has(`person:${tie.targetPersonId}`)) continue;
    byPerson.set(tie.personId, [...(byPerson.get(tie.personId) ?? []), { to_id: tie.targetPersonId, kind: tie.kind, note: tie.notes?.trim() || null }]);
  }
  return shown.map((entity) => ({
    ...entity,
    tags: [...(tagged.get(`${entity.kind}:${entity.id}`) ?? [])].sort(),
    relationships: entity.kind === 'person' ? (byPerson.get(entity.id) ?? []) : null,
  }));
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
  return NextResponse.json({ world_entities: await withTagsAndTies(ownerId, await withSecrecy(found)), next: null });
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
      ...(canonOf === null ? [] : [{ createdById: owner.id, settingId: canonOf, campaignId: null, ...(await notAnotherEra(owner.id, campaignId)), ...changed }]),
    ];
    const rows = await Promise.all(
      scopes.flatMap((where) =>
        (kinds as WorldEntityKind[]).map(async (kind) => (await rowsOf(kind, where)).map((row) => entityOf(kind, row))),
      ),
    );
    const page = pageOf(rows.flat(), after, limit);
    return NextResponse.json({ ...page, world_entities: await withTagsAndTies(owner.id, await withSecrecy(page.world_entities)) });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

const matchingBody = z.object({
  text: z.string(),
  limit: z.number().int().min(1).max(100).default(50),
  include_setting: z.boolean().default(true),
  tags: z.array(z.string()).nullish(),
});

/**
 * POST /v1/campaign/{id}/matching {"matching": {text, limit?, include_setting?, tags?}} →
 * {world_entities, matched: {id: [keys]}}, as the server's world_entities_matching: only the
 * campaign's records (and its setting's canon) whose name, alias or keyword the text names, plus
 * the always-active, most specific first (lib/worldKeys). Lite reads its one owner's names here
 * rather than through a key table; the server's index serves the full libraries.
 */
export async function campaignMatchingPost(request: NextRequest, context: { params: Promise<Record<string, string>> }): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const campaignId = (await context.params).id ?? '';
    const input = parseBody(matchingBody, await readJsonObject(request), 'matching');
    const { shown, matched } = await matchedEntities(owner.id, campaignId, input.text, input.include_setting, input.tags ?? [], input.limit);
    return NextResponse.json({ world_entities: shown, matched });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

/** The campaign's records (and, asked for, its setting's canon) whose name, alias or keyword the text
 * names, plus the always-active, most specific first: the matching route's answer, and lore_search's
 * exact layer. */
export async function matchedEntities(
  ownerId: string,
  campaignId: string,
  text: string,
  includeSetting: boolean,
  tags: readonly string[],
  limit: number,
): Promise<{ shown: Awaited<ReturnType<typeof withTagsAndTies>>; matched: Record<string, string[]> }> {
  const campaign = await prisma.campaign.findFirst({ where: { id: campaignId, createdById: ownerId }, select: { settingId: true } });
  if (campaign === null) throw recordError(404, 'CampaignModel not found');
  const live = { OR: [{ isTemplate: null }, { isTemplate: false }], deletedAt: null };
  const scopes: object[] = [
    { createdById: ownerId, campaignId, ...live },
    ...(includeSetting && campaign.settingId ? [{ createdById: ownerId, settingId: campaign.settingId, campaignId: null, ...(await notAnotherEra(ownerId, campaignId)), ...live }] : []),
  ];
  const rows = (await Promise.all(scopes.flatMap((where) => WORLD_ENTITY_KINDS.map(async (kind) => (await rowsOf(kind, where)).map((row) => entityOf(kind, row)))))).flat();
  const grams = textGrams(text);
  grams.add(ALWAYS);
  const matched = new Map<string, string[]>();
  for (const entity of rows) {
    const keys = recordKeys(entity.name, entity.aliases ?? [], entity.keywords ?? [], entity.lore?.always_active === true).filter((key) => grams.has(key));
    if (keys.length > 0) matched.set(entity.id, keys);
  }
  const weight = (id: string): number => Math.max(...(matched.get(id) ?? []).map((key) => (key === ALWAYS ? 0 : key.split(' ').length)));
  const ranked = rows.filter((entity) => matched.has(entity.id)).sort((one, two) => weight(two.id) - weight(one.id) || one.id.localeCompare(two.id));
  const wanted = new Set(tags.map((tag) => tag.trim().toLocaleLowerCase()).filter((tag) => tag !== ''));
  const shown = (await withTagsAndTies(ownerId, await withSecrecy(ranked)))
    .filter((entity) => wanted.size === 0 || entity.tags.some((tag: string) => wanted.has(tag.toLocaleLowerCase())))
    .slice(0, limit);
  return { shown, matched: Object.fromEntries(shown.map((entity) => [entity.id, [...new Set(matched.get(entity.id))].sort()])) };
}

/** A canon scope's filter keeping out another era's records (none for a setting read alone). */
async function notAnotherEra(ownerId: string, campaignId: string | null): Promise<object> {
  if (campaignId === null) return {};
  const excluded = await eraExcluded(ownerId, campaignId);
  return excluded.length === 0 ? {} : { id: { notIn: excluded } };
}
