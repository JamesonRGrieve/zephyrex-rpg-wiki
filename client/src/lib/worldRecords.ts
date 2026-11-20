// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The lite edition's worlds, places and people: the same resources, fields and rules as the SaaS
 * server's (server/extensions/rpg_core, world_spatial, and genealogy's Person with rpg_core's
 * fields). Kinds and limits come from contract/wiki.json; an entry is stored with its plain text
 * as the description (src/lib/entry.ts). A reference to a world or place must be one of the
 * owner's own, and a place never sits under itself or its own descendants.
 */
import type { Prisma } from '@prisma/client';
import { type ResourceSpec, validationError } from '@zephyrex/lite';
import { z } from 'zod';
import { LIMITS, LOCATION_KINDS, PERSON_KINDS } from '~/contract';
import { type Columns, columnsOf, fieldsOf, plain } from '~/lib/columns';
import { EntryError, parseEntry } from '~/lib/entry';
import { prisma } from '~/lib/prisma';

const name = z.string().trim().min(1, 'A name is required').max(LIMITS.name_characters);
const reference = z.string().min(1).nullable();
const kindOf = (kinds: readonly string[]) => z.enum(kinds as [string, ...string[]]).nullable();
const entry = z.unknown();

/** Stamps, writer, and the entry turned into its stored text and plain-text description. */
function written(columns: Columns, input: Record<string, unknown>, stamp: Date, userId?: string): Record<string, unknown> {
  const data: Record<string, unknown> = { ...input };
  if (data.entry !== undefined && data.entry !== null) {
    try {
      const { stored, text } = parseEntry(data.entry);
      data.entry = stored;
      data.description = text;
    } catch (error) {
      if (error instanceof EntryError) throw validationError(error.message, 'entry');
      throw error;
    }
  }
  return { ...columnsOf(columns, data), updatedAt: stamp, ...(userId === undefined ? {} : { updatedById: userId }) };
}

function filters(query: URLSearchParams, names: readonly [string, string][]): Record<string, string> {
  const where: Record<string, string> = {};
  for (const [field, column] of names) {
    const value = query.get(field);
    if (value !== null && value !== '') where[column] = value;
  }
  return where;
}

async function checkWorld(ownerId: string, campaignId: unknown): Promise<void> {
  if (typeof campaignId !== 'string') return;
  if ((await prisma.campaign.count({ where: { id: campaignId, createdById: ownerId } })) === 0)
    throw validationError('That world is not one of yours', 'campaign_id');
}

async function checkPlace(ownerId: string, locationId: unknown, field: string): Promise<void> {
  if (typeof locationId !== 'string') return;
  if ((await prisma.location.count({ where: { id: locationId, createdById: ownerId } })) === 0)
    throw validationError('That place is not one of yours', field);
}

// ---- campaign (a world) ----------------------------------------------------------------------

const CAMPAIGN_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
};
const campaignCreate = z.object({ name, description: z.string().default('') });
const campaignUpdate = z.object({ name, description: z.string() }).partial();
type CampaignRow = Prisma.CampaignGetPayload<object>;

export const campaigns: ResourceSpec<CampaignRow, z.infer<typeof campaignCreate>, z.infer<typeof campaignUpdate>> = {
  resource: 'campaign',
  plural: 'campaigns',
  modelName: 'CampaignModel',
  createSchema: campaignCreate,
  updateSchema: campaignUpdate,
  list: (ownerId) => prisma.campaign.findMany({ where: { createdById: ownerId }, orderBy: { name: 'asc' } }),
  find: (id, ownerId) => prisma.campaign.findFirst({ where: { id, createdById: ownerId } }),
  insert: (ownerId, input, stamp) =>
    prisma.campaign.create({
      data: { createdById: ownerId, ...written(CAMPAIGN_COLUMNS, input, stamp) } as Prisma.CampaignUncheckedCreateInput,
    }),
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.campaign.updateMany({
      where: { id, updatedAt: version },
      data: written(CAMPAIGN_COLUMNS, input, stamp, userId) as Prisma.CampaignUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.campaign.findUnique({ where: { id } });
  },
  async remove(id) {
    // Its places and people stay, unscoped, as the server's optional foreign keys leave them.
    await prisma.$transaction([
      prisma.location.updateMany({ where: { campaignId: id }, data: { campaignId: null } }),
      prisma.person.updateMany({ where: { campaignId: id }, data: { campaignId: null } }),
      prisma.campaign.delete({ where: { id } }),
    ]);
  },
  // The server's CampaignModel also answers these; lite has no game systems or other owners.
  fields: (row) => ({ ...fieldsOf(CAMPAIGN_COLUMNS, row), game_system_id: null, user_id: null }),
};

// ---- location (a place) ----------------------------------------------------------------------

const LOCATION_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  kind: plain('kind'),
  parent_id: plain('parentId'),
  campaign_id: plain('campaignId'),
};
const locationFields = {
  name,
  description: z.string(),
  entry,
  kind: kindOf(LOCATION_KINDS),
  parent_id: reference,
  campaign_id: reference,
};
const locationCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: locationFields.kind.default(null),
  parent_id: reference.default(null),
  campaign_id: reference.default(null),
});
const locationUpdate = z.object(locationFields).partial();
type LocationRow = Prisma.LocationGetPayload<object>;

/** Refuses a parent that is the place itself or one of its own descendants. */
async function checkNoCycle(id: string, parentId: unknown): Promise<void> {
  if (typeof parentId !== 'string') return;
  const seen = new Set<string>();
  for (let at: string | null = parentId; at !== null; ) {
    if (at === id) throw validationError('A location can’t sit under itself or its own descendants', 'parent_id');
    if (seen.has(at)) return;
    seen.add(at);
    const parent: { parentId: string | null } | null = await prisma.location.findUnique({
      where: { id: at },
      select: { parentId: true },
    });
    at = parent?.parentId ?? null;
  }
}

export const locations: ResourceSpec<LocationRow, z.infer<typeof locationCreate>, z.infer<typeof locationUpdate>> = {
  resource: 'location',
  plural: 'locations',
  modelName: 'LocationModel',
  createSchema: locationCreate,
  updateSchema: locationUpdate,
  list: (ownerId, query) =>
    prisma.location.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['parent_id', 'parentId'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.location.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkPlace(ownerId, input.parent_id, 'parent_id');
    return prisma.location.create({
      data: { createdById: ownerId, ...written(LOCATION_COLUMNS, input, stamp) } as Prisma.LocationUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.location.findUnique({ where: { id }, select: { createdById: true } });
    if (owner !== null) {
      await checkWorld(owner.createdById, input.campaign_id);
      await checkPlace(owner.createdById, input.parent_id, 'parent_id');
    }
    await checkNoCycle(id, input.parent_id);
    const { count } = await prisma.location.updateMany({
      where: { id, updatedAt: version },
      data: written(LOCATION_COLUMNS, input, stamp, userId) as Prisma.LocationUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.location.findUnique({ where: { id } });
  },
  async remove(id) {
    // Its children move up to its parent, and anyone standing in it is nowhere in particular.
    const place = await prisma.location.findUnique({ where: { id }, select: { parentId: true } });
    await prisma.$transaction([
      prisma.location.updateMany({ where: { parentId: id }, data: { parentId: place?.parentId ?? null } }),
      prisma.person.updateMany({ where: { locationId: id }, data: { locationId: null } }),
      prisma.location.delete({ where: { id } }),
    ]);
  },
  fields: (row) => fieldsOf(LOCATION_COLUMNS, row),
};

// ---- person ----------------------------------------------------------------------------------

const PERSON_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  kind: plain('kind'),
  campaign_id: plain('campaignId'),
  location_id: plain('locationId'),
  gender: plain('gender'),
};
const personFields = {
  name,
  description: z.string(),
  entry,
  kind: kindOf(PERSON_KINDS),
  campaign_id: reference,
  location_id: reference,
  gender: z.string().max(LIMITS.name_characters).nullable(),
};
const personCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: personFields.kind.default(null),
  campaign_id: reference.default(null),
  location_id: reference.default(null),
  gender: personFields.gender.default(null),
});
const personUpdate = z.object(personFields).partial();
type PersonRow = Prisma.PersonGetPayload<object>;

export const people: ResourceSpec<PersonRow, z.infer<typeof personCreate>, z.infer<typeof personUpdate>> = {
  resource: 'person',
  plural: 'persons',
  modelName: 'PersonModel',
  createSchema: personCreate,
  updateSchema: personUpdate,
  list: (ownerId, query) =>
    prisma.person.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['location_id', 'locationId'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.person.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkPlace(ownerId, input.location_id, 'location_id');
    return prisma.person.create({
      data: { createdById: ownerId, ...written(PERSON_COLUMNS, input, stamp) } as Prisma.PersonUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.person.findUnique({ where: { id }, select: { createdById: true } });
    if (owner !== null) {
      await checkWorld(owner.createdById, input.campaign_id);
      await checkPlace(owner.createdById, input.location_id, 'location_id');
    }
    const { count } = await prisma.person.updateMany({
      where: { id, updatedAt: version },
      data: written(PERSON_COLUMNS, input, stamp, userId) as Prisma.PersonUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.person.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.person.delete({ where: { id } });
  },
  // The server's Person also answers its genealogy dates and the player; lite has no accounts.
  fields: (row) => ({
    ...fieldsOf(PERSON_COLUMNS, row),
    user_id: null,
    birth_date: row.birthDate?.toISOString() ?? null,
    death_date: row.deathDate?.toISOString() ?? null,
  }),
};
