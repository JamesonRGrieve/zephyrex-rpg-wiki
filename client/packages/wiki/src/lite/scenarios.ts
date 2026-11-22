// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Copy on start, as the server's rpg_core (Scenarios.py, instantiate_campaign): POST
 * /v1/campaign/{id}/instantiate makes a playthrough of a scenario, a new campaign with its own copy
 * of every record (places, organisations, people, items, journals, hooks, tags, statuses) and every
 * link between them (relationships and their influences, hook dependencies, who holds which hook,
 * dispositions, tags and statuses on a record, item instances and what carries them, posts,
 * properties). Each copy's columns are its source's, with every value naming a copied record (a
 * reference, or an id inside JSON text: an entry's mentions, a hook's requirement) turned to its copy;
 * the setting's canon stays shared. Lite gives each copy its id before writing, so one pass in one
 * transaction does it.
 */
import type { Prisma } from '@prisma/client';
import { apiErrorResponse, localOwner, notFound, parseBody, readJsonObject, toDto } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { z } from 'zod';
import { prisma } from './db';
import { pregenRows } from './pregens';
import { campaigns } from './worldRecords';

type Row = Record<string, unknown> & { id: string };
type Context = { params: Promise<Record<string, string>> };

/** What the copier needs of a Prisma model: read rows, write many. */
interface Table {
  findMany(args: object): Promise<Row[]>;
  createMany(args: { data: object[] }): Promise<unknown>;
}
type Tables = Record<string, Table>;

function tableOf(tables: Tables, model: string): Table {
  const table = tables[model];
  if (table === undefined) throw new Error(`The lite schema has no ${model} table`);
  return table;
}

/** The campaign's own records, copied when not templates (as the server, a template stays). */
const RECORDS = ['taxon', 'status', 'location', 'faction', 'person', 'item', 'journal', 'hook'] as const;
const TEMPLATED = new Set(['location', 'faction', 'person', 'item', 'journal', 'hook']);
/** Each link table and the columns that tie a row to a copied record, in an order where every row's anchor is copied first. */
const LINKS: readonly (readonly [string, readonly string[]])[] = [
  ['relationship', ['personId', 'factionId', 'targetPersonId', 'targetFactionId']],
  ['relationInfluence', ['relationshipId']],
  ['hookDependency', ['parentHookId', 'childHookId']],
  ['personHook', ['personId']],
  ['factionHook', ['factionId']],
  ['disposition', ['personId']],
  ['entityTaxon', ['targetEntityId']],
  ['entityStatus', ['targetEntityId']],
  ['entityPost', ['targetEntityId']],
  ['recordMetadata', ['targetEntityId']],
];
/** What a copy never takes: a hook's resolution (a playthrough starts it fresh). */
const CLEARED = new Set(['resolvedAt', 'resolvedJournalId']);

/** A JSON value with every copied id turned to its copy. */
function walked(value: unknown, ids: ReadonlyMap<string, string>): unknown {
  if (typeof value === 'string') return ids.get(value) ?? value;
  if (Array.isArray(value)) return value.map((one) => walked(one, ids));
  if (value !== null && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, one]) => [key, walked(one, ids)]));
  return value;
}

/** A column's value for the copy: a copied id turned to its copy, the same inside JSON text. */
export function remapped(value: unknown, ids: ReadonlyMap<string, string>): unknown {
  if (typeof value !== 'string') return value;
  const direct = ids.get(value);
  if (direct !== undefined) return direct;
  const text = value.trim();
  // JSON text: an object, a list, or a string ('"<id>"', a hook's single requirement).
  if ((text.startsWith('{') || text.startsWith('[') || text.startsWith('"')) && [...ids.keys()].some((id) => text.includes(id))) {
    try {
      return JSON.stringify(walked(JSON.parse(text), ids));
    } catch {
      return value;
    }
  }
  return value;
}

function copyOf(row: Row, ids: ReadonlyMap<string, string>, ownerId: string, stamp: Date): Row {
  const copy: Row = { id: ids.get(row.id) ?? row.id };
  for (const [column, value] of Object.entries(row)) {
    if (column === 'id') continue;
    if (column === 'createdById') copy[column] = ownerId;
    else if (column === 'createdAt' || column === 'updatedAt') copy[column] = stamp;
    else if (column === 'updatedById') copy[column] = null;
    else if (CLEARED.has(column)) copy[column] = null;
    else copy[column] = remapped(value, ids);
  }
  return copy;
}

/** A scenario copied into a new campaign of the owner's; the campaign's row and the id map. */
export async function instantiateCampaign(
  ownerId: string,
  sourceId: string,
  name: string | null,
  pregens: readonly string[] = [],
): Promise<{ campaign: Prisma.CampaignGetPayload<object>; idMap: Record<string, string> }> {
  return prisma.$transaction(async (tx) => {
    // Every model by name, for the one generic copier; each is written only with rows of its own.
    const tables = tx as unknown as Tables;
    const source = await tx.campaign.findFirst({ where: { id: sourceId, createdById: ownerId } });
    if (source === null) throw notFound('CampaignModel');
    const ids = new Map<string, string>([[source.id, crypto.randomUUID()]]);
    const assign = (rows: readonly Row[]): void => {
      for (const row of rows) if (!ids.has(row.id)) ids.set(row.id, crypto.randomUUID());
    };
    const copied: [string, Row[]][] = [];
    for (const model of RECORDS) {
      const table = tableOf(tables, model);
      // eslint-disable-next-line no-await-in-loop -- one model at a time, in the copier's order
      const rows = await table.findMany({
        // Taxons, statuses and the six kinds keep tombstones: a deleted one isn't copied, nor a template.
        // (isTemplate is null or false: NOT { isTemplate: true } would leave out the nulls too.)
        where: { createdById: ownerId, campaignId: source.id, deletedAt: null, ...(TEMPLATED.has(model) ? { OR: [{ isTemplate: null }, { isTemplate: false }] } : {}) },
      });
      assign(rows);
      copied.push([model, rows]);
    }
    // The party's pregens: the setting's characters, copied in as the playthrough's own.
    const picked: Row[] = (await pregenRows(tx, ownerId, source.settingId, pregens)).map((row) => ({ ...(row as Row), campaignId: source.id, settingId: null }));
    assign(picked);
    copied.push(['person', picked]);
    for (const [model, anchors] of LINKS) {
      const table = tableOf(tables, model);
      const known = [...ids.keys()];
      // eslint-disable-next-line no-await-in-loop -- a link's anchor must be copied before it is read
      const rows = await table.findMany({ where: { createdById: ownerId, OR: anchors.map((column) => ({ [column]: { in: known } })) } });
      assign(rows);
      copied.push([model, rows]);
    }
    // What the copied records carry: item instances held or owned, then what holds them.
    const holdings = await tableOf(tables, 'entityInventory').findMany({ where: { createdById: ownerId, targetEntityId: { in: [...ids.keys()] } } });
    const held = holdings.map((one) => String(one.itemInstanceId));
    const instances = await tableOf(tables, 'itemInstance').findMany({ where: { createdById: ownerId, OR: [{ ownerPersonId: { in: [...ids.keys()] } }, { id: { in: held } }] } });
    assign(instances);
    assign(holdings);
    copied.push(['itemInstance', instances], ['entityInventory', holdings]);

    const stamp = new Date();
    const [scenario] = await tableOf(tables, 'campaign').findMany({ where: { id: source.id } });
    if (scenario === undefined) throw notFound('CampaignModel');
    const playthrough = { ...copyOf(scenario, ids, ownerId, stamp), name: name ?? source.name, isScenario: false, scenarioId: source.id };
    await tableOf(tables, 'campaign').createMany({ data: [playthrough] });
    for (const [model, rows] of copied) {
      // eslint-disable-next-line no-await-in-loop -- in order, so each row's anchor is written first
      if (rows.length > 0) await tableOf(tables, model).createMany({ data: rows.map((row) => copyOf(row, ids, ownerId, stamp)) });
    }
    const campaign = await tx.campaign.findUniqueOrThrow({ where: { id: playthrough.id } });
    return { campaign, idMap: Object.fromEntries(ids) };
  });
}

const start = z.object({ name: z.string().trim().min(1).nullish(), pregens: z.array(z.string()).nullish() });

/** A start, as the server's campaign_start rows: lite's copy is one quick transaction, so a start
 * is done (or failed) before it's answered; kept in this process for GET /v1/campaign_start/{id}. */
export interface CampaignStartRow {
  id: string;
  scenario_id: string;
  campaign_id: string | null;
  name: string | null;
  state: 'running' | 'done' | 'failed';
  done: number;
  total: number;
  step: string;
  id_map: string | null;
  error: string | null;
}
/** The server's START_STEPS count (rpg_core), so both editions report the same total. */
const START_STEPS = 13;
const starts = new Map<string, { ownerId: string; row: CampaignStartRow }>();

/** POST /v1/campaign/{id}/instantiate {"instantiate": {name?}} → 202 {start}, as the server answers
 * (there, the copy runs on in the background); GET /v1/campaign_start/{id} has the result. */
export async function campaignInstantiatePost(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const id = (await context.params).id ?? '';
    const input = parseBody(start, await readJsonObject(request), 'instantiate');
    const { campaign, idMap } = await instantiateCampaign(owner.id, id, input.name ?? null, input.pregens ?? []);
    const row: CampaignStartRow = {
      id: crypto.randomUUID(),
      scenario_id: id,
      campaign_id: toDto(campaigns, campaign).id as string,
      name: input.name ?? null,
      state: 'done',
      done: START_STEPS,
      total: START_STEPS,
      step: 'done',
      id_map: JSON.stringify(idMap),
      error: null,
    };
    starts.set(row.id, { ownerId: owner.id, row });
    return NextResponse.json({ start: row }, { status: 202 });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

/** GET /v1/campaign_start/{id}: one's own start. */
export async function campaignStartGet(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const held = starts.get((await context.params).id ?? '');
    if (held === undefined || held.ownerId !== owner.id) throw notFound('CampaignStartModel');
    return NextResponse.json({ campaign_start: held.row });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
