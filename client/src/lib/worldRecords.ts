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
import { ENTITY_TYPES, FACTION_KINDS, ITEM_KINDS, JOURNAL_KINDS, LIMITS, LOCATION_KINDS, PERSON_KINDS, POST_POSITIONS } from '~/contract';
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

/**
 * A deleted place, person, faction or item stays as a tombstone (rpg-ai A15: a since-sync removes its
 * entry), as the server's soft delete keeps it: hidden from every normal read, its updatedAt the
 * moment it went.
 */
function tombstone(): { deletedAt: Date; updatedAt: Date } {
  const now = new Date();
  return { deletedAt: now, updatedAt: now };
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

async function checkPerson(ownerId: string, personId: unknown): Promise<void> {
  if (typeof personId !== 'string') return;
  if ((await prisma.person.count({ where: { deletedAt: null, id: personId, createdById: ownerId } })) === 0)
    throw validationError('That person is not one of yours', 'associated_person_id');
}

/**
 * A record's world is fixed once set (rpg-ai A15's sync), as the server refuses: campaign_id goes
 * from none to a world, never to another world or back to none. Moving is copy and delete.
 */
function checkWorldStays(current: string | null | undefined, wanted: unknown): void {
  if (wanted === undefined || current === null || current === undefined) return;
  if (wanted !== current)
    throw validationError('A record’s world is fixed once set: copy it to another world instead', 'campaign_id');
}

async function checkPlace(ownerId: string, locationId: unknown, field: string): Promise<void> {
  if (typeof locationId !== 'string') return;
  if ((await prisma.location.count({ where: { deletedAt: null, id: locationId, createdById: ownerId } })) === 0)
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
      prisma.faction.updateMany({ where: { campaignId: id }, data: { campaignId: null } }),
      prisma.item.updateMany({ where: { campaignId: id }, data: { campaignId: null } }),
      prisma.campaign.delete({ where: { id } }),
    ]);
  },
  // The server's CampaignModel also answers its owner; lite has one person and no accounts.
  fields: (row) => ({ ...fieldsOf(CAMPAIGN_COLUMNS, row), user_id: null }),
};

// ---- location (a place) ----------------------------------------------------------------------

const LOCATION_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  kind: plain('kind'),
  parent_id: plain('parentId'),
  campaign_id: plain('campaignId'),
  associated_person_id: plain('associatedPersonId'),
};
const locationFields = {
  name,
  description: z.string(),
  entry,
  kind: kindOf(LOCATION_KINDS),
  parent_id: reference,
  campaign_id: reference,
  associated_person_id: reference,
};
const locationCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: locationFields.kind.default(null),
  parent_id: reference.default(null),
  campaign_id: reference.default(null),
  associated_person_id: reference.default(null),
});
const locationUpdate = z.object(locationFields).partial();
type LocationRow = Prisma.LocationGetPayload<object>;

/** Reads a record's parent id from its table, or null when it has none (or isn't there). */
type ParentOf = (id: string) => Promise<string | null>;
const placeParent: ParentOf = async (id) =>
  (await prisma.location.findUnique({ where: { id }, select: { parentId: true } }))?.parentId ?? null;
const factionParent: ParentOf = async (id) =>
  (await prisma.faction.findUnique({ where: { id }, select: { parentId: true } }))?.parentId ?? null;

/** Refuses a parent that is the record itself or one of its own descendants (as the server, 422). */
async function checkNoCycle(id: string, parentId: unknown, parentOf: ParentOf, what: string): Promise<void> {
  if (typeof parentId !== 'string') return;
  const seen = new Set<string>();
  for (let at: string | null = parentId; at !== null; ) {
    if (at === id) throw validationError(`A ${what} can’t sit under itself or its own descendants`, 'parent_id');
    if (seen.has(at)) return;
    seen.add(at);
    at = await parentOf(at);
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
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['parent_id', 'parentId'],
          ['kind', 'kind'],
          ['associated_person_id', 'associatedPersonId'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.location.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkPlace(ownerId, input.parent_id, 'parent_id');
    await checkPerson(ownerId, input.associated_person_id);
    return prisma.location.create({
      data: { createdById: ownerId, ...written(LOCATION_COLUMNS, input, stamp) } as Prisma.LocationUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.location.findUnique({ where: { id }, select: { createdById: true, campaignId: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) {
      await checkWorld(owner.createdById, input.campaign_id);
      await checkPlace(owner.createdById, input.parent_id, 'parent_id');
      await checkPerson(owner.createdById, input.associated_person_id);
    }
    await checkNoCycle(id, input.parent_id, placeParent, 'location');
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
      prisma.itemInstance.updateMany({ where: { locationId: id }, data: { locationId: null } }),
      prisma.entityInventory.deleteMany({ where: { targetEntityType: 'location', targetEntityId: id } }),
      prisma.location.update({ where: { id }, data: tombstone() }),
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
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['location_id', 'locationId'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.person.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkPlace(ownerId, input.location_id, 'location_id');
    return prisma.person.create({
      data: { createdById: ownerId, ...written(PERSON_COLUMNS, input, stamp) } as Prisma.PersonUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.person.findUnique({ where: { id }, select: { createdById: true, campaignId: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
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
    await prisma.$transaction([
      prisma.itemInstance.updateMany({ where: { ownerPersonId: id }, data: { ownerPersonId: null } }),
      prisma.entityInventory.deleteMany({ where: { targetEntityType: 'person', targetEntityId: id } }),
      prisma.location.updateMany({ where: { associatedPersonId: id }, data: { associatedPersonId: null } }),
      prisma.person.update({ where: { id }, data: tombstone() }),
    ]);
  },
  // The server's Person also answers its genealogy dates and the player; lite has no accounts.
  fields: (row) => ({
    ...fieldsOf(PERSON_COLUMNS, row),
    user_id: null,
    birth_date: row.birthDate?.toISOString() ?? null,
    death_date: row.deathDate?.toISOString() ?? null,
  }),
};

// ---- faction (an organisation or family) -----------------------------------------------------

const FACTION_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  kind: plain('kind'),
  parent_id: plain('parentId'),
  campaign_id: plain('campaignId'),
};
const factionCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: kindOf(FACTION_KINDS).default(null),
  parent_id: reference.default(null),
  campaign_id: reference.default(null),
});
const factionUpdate = z
  .object({ name, description: z.string(), entry, kind: kindOf(FACTION_KINDS), parent_id: reference, campaign_id: reference })
  .partial();
type FactionRow = Prisma.FactionGetPayload<object>;

async function checkFaction(ownerId: string, factionId: unknown): Promise<void> {
  if (typeof factionId !== 'string') return;
  if ((await prisma.faction.count({ where: { deletedAt: null, id: factionId, createdById: ownerId } })) === 0)
    throw validationError('That faction is not one of yours', 'parent_id');
}

export const factions: ResourceSpec<FactionRow, z.infer<typeof factionCreate>, z.infer<typeof factionUpdate>> = {
  resource: 'faction',
  plural: 'factions',
  modelName: 'FactionModel',
  createSchema: factionCreate,
  updateSchema: factionUpdate,
  list: (ownerId, query) =>
    prisma.faction.findMany({
      where: {
        createdById: ownerId,
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['parent_id', 'parentId'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.faction.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkFaction(ownerId, input.parent_id);
    return prisma.faction.create({
      data: { createdById: ownerId, ...written(FACTION_COLUMNS, input, stamp) } as Prisma.FactionUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.faction.findUnique({ where: { id }, select: { createdById: true, campaignId: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) {
      await checkWorld(owner.createdById, input.campaign_id);
      await checkFaction(owner.createdById, input.parent_id);
    }
    await checkNoCycle(id, input.parent_id, factionParent, 'faction');
    const { count } = await prisma.faction.updateMany({
      where: { id, updatedAt: version },
      data: written(FACTION_COLUMNS, input, stamp, userId) as Prisma.FactionUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.faction.findUnique({ where: { id } });
  },
  async remove(id) {
    // Its sub-factions move up to its parent, and what it carried is no longer carried.
    const faction = await prisma.faction.findUnique({ where: { id }, select: { parentId: true } });
    await prisma.$transaction([
      prisma.faction.updateMany({ where: { parentId: id }, data: { parentId: faction?.parentId ?? null } }),
      prisma.entityInventory.deleteMany({ where: { targetEntityType: 'faction', targetEntityId: id } }),
      prisma.faction.update({ where: { id }, data: tombstone() }),
    ]);
  },
  fields: (row) => fieldsOf(FACTION_COLUMNS, row),
};

// ---- item (the catalogue) --------------------------------------------------------------------

/** A count of one or more, as the server's checked_quantity. */
const quantity = z.number().int().min(1, 'A quantity is a whole number of one or more');
const amount = z.number().min(0, 'Can’t be below zero').nullable();

const ITEM_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  kind: plain('kind'),
  weight: plain('weight'),
  base_value: plain('baseValue'),
  stack_size: plain('stackSize'),
  campaign_id: plain('campaignId'),
};
const itemCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: kindOf(ITEM_KINDS).default(null),
  weight: amount.default(null),
  base_value: amount.default(null),
  stack_size: quantity.default(1),
  campaign_id: reference.default(null),
});
const itemUpdate = z
  .object({
    name,
    description: z.string(),
    entry,
    kind: kindOf(ITEM_KINDS),
    weight: amount,
    base_value: amount,
    stack_size: quantity,
    campaign_id: reference,
  })
  .partial();
type ItemRow = Prisma.ItemGetPayload<object>;

export const items: ResourceSpec<ItemRow, z.infer<typeof itemCreate>, z.infer<typeof itemUpdate>> = {
  resource: 'item',
  plural: 'items',
  modelName: 'ItemModel',
  createSchema: itemCreate,
  updateSchema: itemUpdate,
  list: (ownerId, query) =>
    prisma.item.findMany({
      where: {
        createdById: ownerId,
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.item.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    return prisma.item.create({
      data: { createdById: ownerId, ...written(ITEM_COLUMNS, input, stamp) } as Prisma.ItemUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.item.findUnique({ where: { id }, select: { createdById: true, campaignId: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkWorld(owner.createdById, input.campaign_id);
    const { count } = await prisma.item.updateMany({
      where: { id, updatedAt: version },
      data: written(ITEM_COLUMNS, input, stamp, userId) as Prisma.ItemUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.item.findUnique({ where: { id } });
  },
  async remove(id) {
    // Its instances go with it, and with them whatever carried them.
    const instances = await prisma.itemInstance.findMany({ where: { itemId: id }, select: { id: true } });
    const ids = instances.map((one) => one.id);
    await prisma.$transaction([
      prisma.entityInventory.deleteMany({ where: { itemInstanceId: { in: ids } } }),
      prisma.entityInventory.deleteMany({ where: { targetEntityType: 'item', targetEntityId: id } }),
      prisma.itemInstance.deleteMany({ where: { itemId: id } }),
      prisma.item.update({ where: { id }, data: tombstone() }),
    ]);
  },
  fields: (row) => fieldsOf(ITEM_COLUMNS, row),
};

// ---- item_instance (one item in the world) ---------------------------------------------------

const INSTANCE_COLUMNS: Columns = {
  item_id: plain('itemId'),
  location_id: plain('locationId'),
  owner_person_id: plain('ownerPersonId'),
  quantity: plain('quantity'),
  durability: plain('durability'),
};
const instanceCreate = z.object({
  item_id: reference.default(null),
  location_id: reference.default(null),
  owner_person_id: reference.default(null),
  quantity: quantity.default(1),
  durability: z.number().nullable().default(null),
});
const instanceUpdate = z
  .object({ location_id: reference, owner_person_id: reference, quantity, durability: z.number().nullable() })
  .partial();
type InstanceRow = Prisma.ItemInstanceGetPayload<object>;

async function checkOwned(
  ownerId: string,
  value: unknown,
  count: (where: { id: string; createdById: string }) => Promise<number>,
  message: string,
  field: string,
): Promise<void> {
  if (typeof value !== 'string') return;
  if ((await count({ id: value, createdById: ownerId })) === 0) throw validationError(message, field);
}

async function checkInstanceRefs(ownerId: string, input: Record<string, unknown>): Promise<void> {
  await checkOwned(ownerId, input.item_id, (where) => prisma.item.count({ where: { ...where, deletedAt: null } }), 'That item is not one of yours', 'item_id');
  await checkPlace(ownerId, input.location_id, 'location_id');
  await checkOwned(
    ownerId,
    input.owner_person_id,
    (where) => prisma.person.count({ where: { ...where, deletedAt: null } }),
    'That person is not one of yours',
    'owner_person_id',
  );
}

export const itemInstances: ResourceSpec<InstanceRow, z.infer<typeof instanceCreate>, z.infer<typeof instanceUpdate>> = {
  resource: 'item_instance',
  plural: 'item_instances',
  modelName: 'ItemInstanceModel',
  createSchema: instanceCreate,
  updateSchema: instanceUpdate,
  list: (ownerId, query) =>
    prisma.itemInstance.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['item_id', 'itemId'],
          ['location_id', 'locationId'],
          ['owner_person_id', 'ownerPersonId'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.itemInstance.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkInstanceRefs(ownerId, input);
    return prisma.itemInstance.create({
      data: { createdById: ownerId, ...written(INSTANCE_COLUMNS, input, stamp) } as Prisma.ItemInstanceUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.itemInstance.findUnique({ where: { id }, select: { createdById: true } });
    if (owner !== null) await checkInstanceRefs(owner.createdById, input);
    const { count } = await prisma.itemInstance.updateMany({
      where: { id, updatedAt: version },
      data: written(INSTANCE_COLUMNS, input, stamp, userId) as Prisma.ItemInstanceUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.itemInstance.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.$transaction([
      prisma.entityInventory.deleteMany({ where: { itemInstanceId: id } }),
      prisma.itemInstance.delete({ where: { id } }),
    ]);
  },
  fields: (row) => fieldsOf(INSTANCE_COLUMNS, row),
};

// ---- entity_inventory (what an entity carries, W8) -------------------------------------------

const INVENTORY_COLUMNS: Columns = {
  target_entity_type: plain('targetEntityType'),
  target_entity_id: plain('targetEntityId'),
  item_instance_id: plain('itemInstanceId'),
  quantity: plain('quantity'),
};
const inventoryCreate = z.object({
  target_entity_type: z.enum(ENTITY_TYPES as [string, ...string[]]),
  target_entity_id: z.string().min(1),
  item_instance_id: reference.default(null),
  quantity: quantity.default(1),
});
const inventoryUpdate = z.object({ quantity }).partial();
type InventoryRow = Prisma.EntityInventoryGetPayload<object>;

export const entityInventories: ResourceSpec<InventoryRow, z.infer<typeof inventoryCreate>, z.infer<typeof inventoryUpdate>> = {
  resource: 'entity_inventory',
  plural: 'entity_inventories',
  modelName: 'EntityInventoryModel',
  createSchema: inventoryCreate,
  updateSchema: inventoryUpdate,
  list: (ownerId, query) =>
    prisma.entityInventory.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['target_entity_type', 'targetEntityType'],
          ['target_entity_id', 'targetEntityId'],
          ['item_instance_id', 'itemInstanceId'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.entityInventory.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    // The carrier is polymorphic, so unchecked here as on the server (OBJECT_PLAN §7); the
    // instance it carries is a real reference, and must be one of the owner's.
    await checkOwned(
      ownerId,
      input.item_instance_id,
      (where) => prisma.itemInstance.count({ where }),
      'That item is not one of yours',
      'item_instance_id',
    );
    return prisma.entityInventory.create({
      data: { createdById: ownerId, ...written(INVENTORY_COLUMNS, input, stamp) } as Prisma.EntityInventoryUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.entityInventory.updateMany({
      where: { id, updatedAt: version },
      data: written(INVENTORY_COLUMNS, input, stamp, userId) as Prisma.EntityInventoryUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.entityInventory.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.entityInventory.delete({ where: { id } });
  },
  fields: (row) => fieldsOf(INVENTORY_COLUMNS, row),
};

// ---- journal (session reports, diaries, lore, notes…) ---------------------------------------

const JOURNAL_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  kind: plain('kind'),
  location_id: plain('locationId'),
  author_person_id: plain('authorPersonId'),
  session_number: plain('sessionNumber'),
  occurred_at: plain('occurredAt'),
  campaign_id: plain('campaignId'),
};
const sessionNumber = z.number().int().min(1, 'A session number is a whole number of one or more').nullable();
const moment = z.coerce.date().nullable();
const journalCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: kindOf(JOURNAL_KINDS).default(null),
  location_id: reference.default(null),
  author_person_id: reference.default(null),
  session_number: sessionNumber.default(null),
  occurred_at: moment.default(null),
  campaign_id: reference.default(null),
});
const journalUpdate = z
  .object({
    name,
    description: z.string(),
    entry,
    kind: kindOf(JOURNAL_KINDS),
    location_id: reference,
    author_person_id: reference,
    session_number: sessionNumber,
    occurred_at: moment,
    campaign_id: reference,
  })
  .partial();
type JournalRow = Prisma.JournalGetPayload<object>;

async function checkJournalRefs(ownerId: string, input: Record<string, unknown>): Promise<void> {
  await checkWorld(ownerId, input.campaign_id);
  await checkPlace(ownerId, input.location_id, 'location_id');
  await checkOwned(
    ownerId,
    input.author_person_id,
    (where) => prisma.person.count({ where: { ...where, deletedAt: null } }),
    'That person is not one of yours',
    'author_person_id',
  );
}

export const journals: ResourceSpec<JournalRow, z.infer<typeof journalCreate>, z.infer<typeof journalUpdate>> = {
  resource: 'journal',
  plural: 'journals',
  modelName: 'JournalModel',
  createSchema: journalCreate,
  updateSchema: journalUpdate,
  list: (ownerId, query) =>
    prisma.journal.findMany({
      where: {
        createdById: ownerId,
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['kind', 'kind'],
          ['location_id', 'locationId'],
          ['author_person_id', 'authorPersonId'],
        ]),
      },
      orderBy: [{ occurredAt: 'desc' }, { name: 'asc' }],
    }),
  find: (id, ownerId) => prisma.journal.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkJournalRefs(ownerId, input);
    return prisma.journal.create({
      data: { createdById: ownerId, ...written(JOURNAL_COLUMNS, input, stamp) } as Prisma.JournalUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.journal.findUnique({ where: { id }, select: { createdById: true, campaignId: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkJournalRefs(owner.createdById, input);
    const { count } = await prisma.journal.updateMany({
      where: { id, updatedAt: version },
      data: written(JOURNAL_COLUMNS, input, stamp, userId) as Prisma.JournalUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.journal.findUnique({ where: { id } });
  },
  async remove(id) {
    // Its posts stay, as the server's polymorphic posts do (no cascade on a target).
    await prisma.journal.update({ where: { id }, data: tombstone() });
  },
  fields: (row) => ({ ...fieldsOf(JOURNAL_COLUMNS, row), occurred_at: row.occurredAt?.toISOString() ?? null }),
};

// ---- entity_post (a post on any entity, W3) --------------------------------------------------

const POST_COLUMNS: Columns = {
  target_entity_type: plain('targetEntityType'),
  target_entity_id: plain('targetEntityId'),
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  position: plain('position'),
  ordinal: plain('ordinal'),
};
const position = z.enum(POST_POSITIONS as [string, ...string[]]);
const ordinal = z.number().int().min(0, 'An ordinal is a whole number of zero or more');
const postCreate = z.object({
  target_entity_type: z.enum(ENTITY_TYPES as [string, ...string[]]),
  target_entity_id: z.string().min(1),
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  position: position.default('default'),
  ordinal: ordinal.default(0),
});
const postUpdate = z.object({ name, description: z.string(), entry, position, ordinal }).partial();
type PostRow = Prisma.EntityPostGetPayload<object>;

export const entityPosts: ResourceSpec<PostRow, z.infer<typeof postCreate>, z.infer<typeof postUpdate>> = {
  resource: 'entity_post',
  plural: 'entity_posts',
  modelName: 'EntityPostModel',
  createSchema: postCreate,
  updateSchema: postUpdate,
  list: (ownerId, query) =>
    prisma.entityPost.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['target_entity_type', 'targetEntityType'],
          ['target_entity_id', 'targetEntityId'],
          ['position', 'position'],
        ]),
      },
      // pinned_top sorts before default; then by ordinal.
      orderBy: [{ position: 'desc' }, { ordinal: 'asc' }, { createdAt: 'asc' }],
    }),
  find: (id, ownerId) => prisma.entityPost.findFirst({ where: { id, createdById: ownerId } }),
  insert: (ownerId, input, stamp) =>
    prisma.entityPost.create({
      data: { createdById: ownerId, ...written(POST_COLUMNS, input, stamp) } as Prisma.EntityPostUncheckedCreateInput,
    }),
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.entityPost.updateMany({
      where: { id, updatedAt: version },
      data: written(POST_COLUMNS, input, stamp, userId) as Prisma.EntityPostUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.entityPost.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.entityPost.delete({ where: { id } });
  },
  fields: (row) => fieldsOf(POST_COLUMNS, row),
};
