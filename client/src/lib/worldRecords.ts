// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The lite edition's worlds, places and people: the same resources, fields and rules as the SaaS
 * server's (server/extensions/rpg_core, world_spatial, and genealogy's Person with rpg_core's
 * fields). Kinds and limits come from contract/wiki.json; an entry is stored with its plain text
 * as the description (src/lib/entry.ts). A reference to a world or place must be one of the
 * owner's own, and a place never sits under itself or its own descendants.
 */
import type { Prisma } from '@prisma/client';
import { ApiError, notFound, type ResourceSpec, STATUS, validationError } from '@zephyrex/lite';
import { z } from 'zod';
import {
  ENTITY_TYPES,
  FACTION_KINDS,
  HOOK_KINDS,
  ITEM_KINDS,
  JOURNAL_KINDS,
  LIMITS,
  LOCATION_KINDS,
  PERSON_KINDS,
  ATTITUDE_NUANCES,
  ATTITUDES,
  CANON_LEVELS,
  DISPOSITION_TARGETS,
  POST_POSITIONS,
  SEED_SETTINGS,
  STATUS_KINDS,
  TAXON_KINDS,
} from '@zephyrex-rpg/wiki/contract';
import { type Columns, columnsOf, fieldsOf, plain } from '~/lib/columns';
import { EntryError, parseEntry } from '@zephyrex-rpg/wiki/lib/entry';
import { wouldCloseCycle } from '@zephyrex-rpg/wiki/lib/hookGraph';
import { checkedRequirement, leavesOf, RequirementError } from '@zephyrex-rpg/wiki/lib/requirements';
import { prisma } from '~/lib/prisma';
import { checkedKit, KitError } from '@zephyrex-rpg/wiki/lib/properties';
import { lore } from '@zephyrex-rpg/wiki/lib/lore';
import { names, voice } from '@zephyrex-rpg/wiki/lib/names';
import { freeSlug, isSlug, SLUG_RULE, slugify } from '@zephyrex-rpg/wiki/lib/slug';

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

const canonLevel = kindOf(CANON_LEVELS);

/** S4c: a list of names (aliases, keywords), kept as JSON text, as the server's. */
const nameList = z.unknown().transform((value, context) => {
  try {
    return JSON.stringify(names(value));
  } catch (error) {
    context.addIssue({ code: 'custom', message: error instanceof Error ? error.message : String(error) });
    return z.NEVER;
  }
});

/** S4d: a record's lorebook activation, kept as JSON text, as the server's. */
const loreText = z.unknown().transform((value, context) => {
  try {
    return JSON.stringify(lore(value));
  } catch (error) {
    context.addIssue({ code: 'custom', message: error instanceof Error ? error.message : String(error) });
    return z.NEVER;
  }
});

/** S4c: a person's AI voice, kept as JSON text, as the server's. */
const voiceText = z.unknown().transform((value, context) => {
  try {
    return JSON.stringify(voice(value));
  } catch (error) {
    context.addIssue({ code: 'custom', message: error instanceof Error ? error.message : String(error) });
    return z.NEVER;
  }
});

/** S4b, as the server's rpg_core: a record is a template or not from its creation (making one is a copy). */
function checkTemplateStays(current: boolean | null, wanted: boolean | null | undefined): void {
  if (wanted === undefined || wanted === null) return;
  if (wanted !== Boolean(current))
    throw validationError('A record is a template or not from its creation: copy it instead', 'is_template');
}

/**
 * S6, as the server's rpg_core refuses: a record's setting is one of the owner's, fixed once set,
 * and the same as its campaign's (a campaign's record belongs to its campaign's setting).
 */
async function checkSetting(
  ownerId: string,
  input: Record<string, unknown>,
  current: { settingId: string | null; campaignId: string | null } | null,
): Promise<void> {
  const wanted = input.setting_id;
  if (current?.settingId && wanted !== undefined && wanted !== current.settingId)
    throw validationError('A record’s setting is fixed once set: copy it to another setting instead', 'setting_id');
  const setting = wanted === undefined ? (current?.settingId ?? null) : wanted;
  const campaign = input.campaign_id === undefined ? (current?.campaignId ?? null) : input.campaign_id;
  if (typeof setting !== 'string') return;
  if ((await prisma.setting.count({ where: { id: setting, ...seenBy(ownerId) } })) === 0)
    throw validationError('That setting is not one of yours', 'setting_id');
  if (typeof campaign === 'string') {
    const enclosing = await prisma.campaign.findUnique({ where: { id: campaign }, select: { settingId: true } });
    if (enclosing !== null && enclosing.settingId !== setting)
      throw validationError('A campaign’s record belongs to its campaign’s setting', 'setting_id');
  }
}

async function checkPlace(ownerId: string, locationId: unknown, field: string): Promise<void> {
  if (typeof locationId !== 'string') return;
  if ((await prisma.location.count({ where: { deletedAt: null, id: locationId, createdById: ownerId } })) === 0)
    throw validationError('That place is not one of yours', field);
}

// ---- campaign (a world) ----------------------------------------------------------------------

// ---- setting (S6: the universe campaigns take place in; its canon is its campaign-less records) ----

/** The framework's SYSTEM user, as the server's: its records are everyone's to read and nobody else's to change. */
export const SYSTEM_OWNER_ID = 'FFFFFFFF-FFFF-FFFF-AAAA-FFFFFFFFFFFF';

/** The settings `ownerId` sees: their own and the system's (S6b's seeded ones). */
export function seenBy(ownerId: string): { createdById: { in: string[] } } {
  return { createdById: { in: [ownerId, SYSTEM_OWNER_ID] } };
}

let seeding: Promise<void> | null = null;

/**
 * S6b, as the server's rpg_core 006: settings made before slugs get their name's, oldest first, and
 * the contract's seed_settings are the system's, each once by slug. Once per process.
 */
export async function ensureSeedSettings(): Promise<void> {
  seeding ??= seedSettings();
  try {
    await seeding;
  } catch (error) {
    // A failed attempt is tried again on the next request.
    seeding = null;
    throw error;
  }
}

async function seedSettings(): Promise<void> {
  const rows = await prisma.setting.findMany({ orderBy: [{ createdAt: 'asc' }, { id: 'asc' }] });
  const taken = new Set(rows.flatMap((row) => (row.slug === null ? [] : [row.slug])));
  for (const row of rows.filter((one) => one.slug === null)) {
    const slug = freeSlug(slugify(row.name), (candidate) => taken.has(candidate));
    taken.add(slug);
    // eslint-disable-next-line no-await-in-loop -- one row at a time keeps each slug free
    await prisma.setting.update({ where: { id: row.id }, data: { slug } });
  }
  const missing = SEED_SETTINGS.filter((one) => !taken.has(one.slug));
  if (missing.length > 0) {
    await prisma.setting.createMany({
      data: missing.map((one) => ({ createdById: SYSTEM_OWNER_ID, name: one.name, slug: one.slug, updatedAt: new Date() })),
    });
  }
}

/** As the server: a seeded setting reads as missing to anyone changing it, as the framework says of any record one may not change. */
const refuseSystems = (row: { createdById: string } | null): void => {
  if (row?.createdById === SYSTEM_OWNER_ID) throw notFound('SettingModel');
};

const slugInput = z.string().refine(isSlug, SLUG_RULE);

const SETTING_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  slug: plain('slug'),
};
const settingCreate = z.object({ name, description: z.string().default(''), entry: entry.optional(), slug: slugInput.optional() });
const settingUpdate = z.object({ name, description: z.string(), entry, slug: slugInput }).partial();
type SettingRow = Prisma.SettingGetPayload<object>;

// Numbered slugs keep at least this much of the name (the contract's length less a suffix like -9999).
const SLUG_PREFIX = 50;

const slugTaken = async (slug: string): Promise<boolean> => (await prisma.setting.count({ where: { slug } })) > 0;

/** The slug given (409 when another setting holds it), or its name's numbered past any taken, as the server's. */
async function settingSlug(input: { name: string; slug?: string }): Promise<string> {
  if (input.slug !== undefined) {
    if (await slugTaken(input.slug)) throw new ApiError(STATUS.CONFLICT, 'Another setting already has that slug');
    return input.slug;
  }
  const taken = new Set(
    (await prisma.setting.findMany({ where: { slug: { startsWith: slugify(input.name).slice(0, SLUG_PREFIX) } }, select: { slug: true } })).flatMap(
      (row) => (row.slug === null ? [] : [row.slug]),
    ),
  );
  return freeSlug(slugify(input.name), (candidate) => taken.has(candidate));
}

export const settings: ResourceSpec<SettingRow, z.infer<typeof settingCreate>, z.infer<typeof settingUpdate>> = {
  resource: 'setting',
  plural: 'settings',
  modelName: 'SettingModel',
  createSchema: settingCreate,
  updateSchema: settingUpdate,
  async list(ownerId) {
    await ensureSeedSettings();
    return prisma.setting.findMany({ where: seenBy(ownerId), orderBy: { name: 'asc' } });
  },
  async find(id, ownerId) {
    await ensureSeedSettings();
    return prisma.setting.findFirst({ where: { id, ...seenBy(ownerId) } });
  },
  async insert(ownerId, input, stamp) {
    await ensureSeedSettings();
    const slug = await settingSlug(input);
    return prisma.setting.create({
      data: { createdById: ownerId, ...written(SETTING_COLUMNS, { ...input, slug }, stamp) } as Prisma.SettingUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const held = await prisma.setting.findUnique({ where: { id }, select: { createdById: true, slug: true } });
    refuseSystems(held);
    if (input.slug !== undefined && input.slug !== held?.slug) throw validationError('A setting’s slug is fixed once set', 'slug');
    const { count } = await prisma.setting.updateMany({
      where: { id, updatedAt: version },
      data: written(SETTING_COLUMNS, input, stamp, userId) as Prisma.SettingUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.setting.findUnique({ where: { id } });
  },
  async remove(id) {
    refuseSystems(await prisma.setting.findUnique({ where: { id }, select: { createdById: true } }));
    // Its campaigns and canon stay, unscoped, as the server's optional foreign keys leave them.
    await prisma.$transaction([
      prisma.campaign.updateMany({ where: { settingId: id }, data: { settingId: null } }),
      ...(['location', 'person', 'faction', 'item', 'journal', 'hook', 'taxon', 'status'] as const).map((model) =>
        (prisma[model] as unknown as { updateMany: (args: object) => Prisma.PrismaPromise<unknown> }).updateMany({
          where: { settingId: id },
          data: { settingId: null },
        }),
      ),
      prisma.setting.delete({ where: { id } }),
    ]);
  },
  fields: (row) => fieldsOf(SETTING_COLUMNS, row),
};

const CAMPAIGN_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  setting_id: plain('settingId'),
};
const campaignCreate = z.object({ name, description: z.string().default(''), setting_id: reference.default(null) });
const campaignUpdate = z.object({ name, description: z.string(), setting_id: reference }).partial();
type CampaignRow = Prisma.CampaignGetPayload<object>;

/** A campaign's setting is one of the owner's, and fixed once set (as the server's). */
async function checkCampaignSetting(ownerId: string, wanted: unknown, held: string | null): Promise<void> {
  if (held !== null && wanted !== undefined && wanted !== held)
    throw validationError('A campaign’s setting is fixed once set', 'setting_id');
  if (typeof wanted === 'string' && (await prisma.setting.count({ where: { id: wanted, ...seenBy(ownerId) } })) === 0)
    throw validationError('That setting is not one of yours', 'setting_id');
}

export const campaigns: ResourceSpec<CampaignRow, z.infer<typeof campaignCreate>, z.infer<typeof campaignUpdate>> = {
  resource: 'campaign',
  plural: 'campaigns',
  modelName: 'CampaignModel',
  createSchema: campaignCreate,
  updateSchema: campaignUpdate,
  list: (ownerId) => prisma.campaign.findMany({ where: { createdById: ownerId }, orderBy: { name: 'asc' } }),
  find: (id, ownerId) => prisma.campaign.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkCampaignSetting(ownerId, input.setting_id, null);
    return prisma.campaign.create({
      data: { createdById: ownerId, ...written(CAMPAIGN_COLUMNS, input, stamp) } as Prisma.CampaignUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const held = await prisma.campaign.findUnique({ where: { id }, select: { createdById: true, settingId: true } });
    if (held !== null) await checkCampaignSetting(held.createdById, input.setting_id, held.settingId);
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
  setting_id: plain('settingId'),
  canon_level: plain('canonLevel'),
  is_template: plain('isTemplate'),
  aliases: plain('aliases'),
  keywords: plain('keywords'),
  lore: plain('lore'),
  associated_person_id: plain('associatedPersonId'),
};
const locationFields = {
  name,
  description: z.string(),
  entry,
  kind: kindOf(LOCATION_KINDS),
  parent_id: reference,
  campaign_id: reference,
  setting_id: reference,
  canon_level: canonLevel,
  is_template: z.boolean().nullable(),
  aliases: nameList,
  keywords: nameList,
  lore: loreText,
  associated_person_id: reference,
};
const locationCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: locationFields.kind.default(null),
  parent_id: reference.default(null),
  campaign_id: reference.default(null),
  setting_id: reference.default(null),
  canon_level: canonLevel.default(null),
  is_template: z.boolean().nullable().default(null),
  aliases: nameList.optional(),
  keywords: nameList.optional(),
  lore: loreText.optional(),
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
          ['setting_id', 'settingId'],
          ['canon_level', 'canonLevel'],
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
    await checkSetting(ownerId, input, null);
    await checkPlace(ownerId, input.parent_id, 'parent_id');
    await checkPerson(ownerId, input.associated_person_id);
    return prisma.location.create({
      data: { createdById: ownerId, ...written(LOCATION_COLUMNS, input, stamp) } as Prisma.LocationUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.location.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true, isTemplate: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    checkTemplateStays(owner?.isTemplate ?? null, input.is_template);
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
  setting_id: plain('settingId'),
  canon_level: plain('canonLevel'),
  is_template: plain('isTemplate'),
  aliases: plain('aliases'),
  keywords: plain('keywords'),
  lore: plain('lore'),
  voice: plain('voice'),
  location_id: plain('locationId'),
  gender: plain('gender'),
};
const personFields = {
  name,
  description: z.string(),
  entry,
  kind: kindOf(PERSON_KINDS),
  campaign_id: reference,
  setting_id: reference,
  canon_level: canonLevel,
  is_template: z.boolean().nullable(),
  aliases: nameList,
  keywords: nameList,
  lore: loreText,
  voice: voiceText,
  location_id: reference,
  gender: z.string().max(LIMITS.name_characters).nullable(),
};
const personCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: personFields.kind.default(null),
  campaign_id: reference.default(null),
  setting_id: reference.default(null),
  canon_level: canonLevel.default(null),
  is_template: z.boolean().nullable().default(null),
  aliases: nameList.optional(),
  keywords: nameList.optional(),
  lore: loreText.optional(),
  voice: voiceText.optional(),
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
          ['setting_id', 'settingId'],
          ['canon_level', 'canonLevel'],
          ['location_id', 'locationId'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.person.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkSetting(ownerId, input, null);
    await checkPlace(ownerId, input.location_id, 'location_id');
    return prisma.person.create({
      data: { createdById: ownerId, ...written(PERSON_COLUMNS, input, stamp) } as Prisma.PersonUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.person.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true, isTemplate: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    checkTemplateStays(owner?.isTemplate ?? null, input.is_template);
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
  setting_id: plain('settingId'),
  canon_level: plain('canonLevel'),
  is_template: plain('isTemplate'),
  aliases: plain('aliases'),
  keywords: plain('keywords'),
  lore: plain('lore'),
};
const factionCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: kindOf(FACTION_KINDS).default(null),
  parent_id: reference.default(null),
  campaign_id: reference.default(null),
  setting_id: reference.default(null),
  canon_level: canonLevel.default(null),
  is_template: z.boolean().nullable().default(null),
  aliases: nameList.optional(),
  keywords: nameList.optional(),
  lore: loreText.optional(),
});
const factionUpdate = z
  .object({ name, description: z.string(), entry, kind: kindOf(FACTION_KINDS), parent_id: reference, campaign_id: reference, setting_id: reference, canon_level: canonLevel, is_template: z.boolean().nullable(), aliases: nameList, keywords: nameList, lore: loreText })
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
          ['setting_id', 'settingId'],
          ['canon_level', 'canonLevel'],
          ['parent_id', 'parentId'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.faction.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkSetting(ownerId, input, null);
    await checkFaction(ownerId, input.parent_id);
    return prisma.faction.create({
      data: { createdById: ownerId, ...written(FACTION_COLUMNS, input, stamp) } as Prisma.FactionUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.faction.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true, isTemplate: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    checkTemplateStays(owner?.isTemplate ?? null, input.is_template);
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
  setting_id: plain('settingId'),
  canon_level: plain('canonLevel'),
  is_template: plain('isTemplate'),
  aliases: plain('aliases'),
  keywords: plain('keywords'),
  lore: plain('lore'),
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
  setting_id: reference.default(null),
  canon_level: canonLevel.default(null),
  is_template: z.boolean().nullable().default(null),
  aliases: nameList.optional(),
  keywords: nameList.optional(),
  lore: loreText.optional(),
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
    setting_id: reference,
    canon_level: canonLevel,
    is_template: z.boolean().nullable(),
    aliases: nameList,
    keywords: nameList,
    lore: loreText,
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
          ['setting_id', 'settingId'],
          ['canon_level', 'canonLevel'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.item.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkSetting(ownerId, input, null);
    return prisma.item.create({
      data: { createdById: ownerId, ...written(ITEM_COLUMNS, input, stamp) } as Prisma.ItemUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.item.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true, isTemplate: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    checkTemplateStays(owner?.isTemplate ?? null, input.is_template);
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
  setting_id: plain('settingId'),
  canon_level: plain('canonLevel'),
  is_template: plain('isTemplate'),
  aliases: plain('aliases'),
  keywords: plain('keywords'),
  lore: plain('lore'),
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
  setting_id: reference.default(null),
  canon_level: canonLevel.default(null),
  is_template: z.boolean().nullable().default(null),
  aliases: nameList.optional(),
  keywords: nameList.optional(),
  lore: loreText.optional(),
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
    setting_id: reference,
    canon_level: canonLevel,
    is_template: z.boolean().nullable(),
    aliases: nameList,
    keywords: nameList,
    lore: loreText,
  })
  .partial();
type JournalRow = Prisma.JournalGetPayload<object>;

async function checkJournalRefs(ownerId: string, input: Record<string, unknown>): Promise<void> {
  await checkWorld(ownerId, input.campaign_id);
    await checkSetting(ownerId, input, null);
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
          ['setting_id', 'settingId'],
          ['canon_level', 'canonLevel'],
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
    const owner = await prisma.journal.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true, isTemplate: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    checkTemplateStays(owner?.isTemplate ?? null, input.is_template);
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

// ---- property_kit (S4b, world_properties: keys with types and defaults, applied to records) ----

const KIT_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  properties: plain('properties'),
  campaign_id: plain('campaignId'),
  setting_id: plain('settingId'),
};
/** A kit's properties arrive as JSON (a string or the list) and are kept as JSON text, as the server. */
const kitProperties = z.unknown().transform((value, context) => {
  try {
    return JSON.stringify(checkedKit(typeof value === 'string' ? JSON.parse(value) : value));
  } catch (error) {
    context.addIssue({ code: 'custom', message: error instanceof KitError || error instanceof SyntaxError ? error.message : String(error) });
    return z.NEVER;
  }
});
const kitCreate = z.object({
  name,
  description: z.string().default(''),
  properties: kitProperties.default('[]'),
  campaign_id: reference.default(null),
  setting_id: reference.default(null),
});
const kitUpdate = z.object({ name, description: z.string(), properties: kitProperties, campaign_id: reference, setting_id: reference }).partial();
type KitRow = Prisma.PropertyKitGetPayload<object>;

export const propertyKits: ResourceSpec<KitRow, z.infer<typeof kitCreate>, z.infer<typeof kitUpdate>> = {
  resource: 'property_kit',
  plural: 'property_kits',
  modelName: 'PropertyKitModel',
  createSchema: kitCreate,
  updateSchema: kitUpdate,
  list: (ownerId, query) =>
    prisma.propertyKit.findMany({
      where: {
        createdById: ownerId,
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['setting_id', 'settingId'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.propertyKit.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkSetting(ownerId, input, null);
    return prisma.propertyKit.create({
      data: { createdById: ownerId, ...written(KIT_COLUMNS, input, stamp) } as Prisma.PropertyKitUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.propertyKit.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    const { count } = await prisma.propertyKit.updateMany({
      where: { id, updatedAt: version },
      data: written(KIT_COLUMNS, input, stamp, userId) as Prisma.PropertyKitUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.propertyKit.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.propertyKit.update({ where: { id }, data: tombstone() });
  },
  fields: (row) => fieldsOf(KIT_COLUMNS, row),
};

// ---- hook (the plot-hook DAG and who is on each hook) ----------------------------------------

const HOOK_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  entry: plain('entry'),
  kind: plain('kind'),
  giver_person_id: plain('giverPersonId'),
  giver_faction_id: plain('giverFactionId'),
  requires: plain('requires'),
  excuse: plain('excuse'),
  resolved_at: plain('resolvedAt'),
  resolved_journal_id: plain('resolvedJournalId'),
  campaign_id: plain('campaignId'),
  setting_id: plain('settingId'),
  canon_level: plain('canonLevel'),
  is_template: plain('isTemplate'),
  aliases: plain('aliases'),
  keywords: plain('keywords'),
  lore: plain('lore'),
};
const hookCreate = z.object({
  name,
  description: z.string().default(''),
  entry: entry.optional(),
  kind: kindOf(HOOK_KINDS).default(null),
  giver_person_id: reference.default(null),
  giver_faction_id: reference.default(null),
  requires: z.unknown().default(null),
  excuse: z.string().nullable().default(null),
  resolved_at: z.coerce.date().nullable().default(null),
  resolved_journal_id: reference.default(null),
  campaign_id: reference.default(null),
  setting_id: reference.default(null),
  canon_level: canonLevel.default(null),
  is_template: z.boolean().nullable().default(null),
  aliases: nameList.optional(),
  keywords: nameList.optional(),
  lore: loreText.optional(),
});
const hookUpdate = z
  .object({
    name,
    description: z.string(),
    entry,
    kind: kindOf(HOOK_KINDS),
    giver_person_id: reference,
    giver_faction_id: reference,
    requires: z.unknown(),
    excuse: z.string().nullable(),
    resolved_at: z.coerce.date().nullable(),
    resolved_journal_id: reference,
    campaign_id: reference,
    setting_id: reference,
    canon_level: canonLevel,
    is_template: z.boolean().nullable(),
    aliases: nameList,
    keywords: nameList,
    lore: loreText,
  })
  .partial();
type HookRow = Prisma.HookGetPayload<object>;

const livePerson = (where: { id: string; createdById: string }) => prisma.person.count({ where: { ...where, deletedAt: null } });
const liveFaction = (where: { id: string; createdById: string }) => prisma.faction.count({ where: { ...where, deletedAt: null } });
const liveHook = (where: { id: string; createdById: string }) => prisma.hook.count({ where: { ...where, deletedAt: null } });

async function checkHookRefs(ownerId: string, input: Record<string, unknown>): Promise<void> {
  await checkWorld(ownerId, input.campaign_id);
    await checkSetting(ownerId, input, null);
  await checkOwned(ownerId, input.giver_person_id, livePerson, 'That person is not one of yours', 'giver_person_id');
  await checkOwned(ownerId, input.giver_faction_id, liveFaction, 'That organisation is not one of yours', 'giver_faction_id');
}

/** A requirement as it arrives (JSON text, a hook id or the structure) as stored JSON text, or null. */
function requirementText(value: unknown): string | null {
  if (value === null || value === undefined || value === '') return null;
  let node: unknown = value;
  try {
    if (typeof value === 'string' && /^[[{"]/.test(value)) node = JSON.parse(value) as unknown;
    const checked = checkedRequirement(node);
    if (leavesOf(checked).length > LIMITS.requirement_leaves)
      throw new RequirementError(`A requirement names at most ${LIMITS.requirement_leaves} hooks`);
    return JSON.stringify(checked);
  } catch (error) {
    if (error instanceof RequirementError || error instanceof SyntaxError) throw validationError(error.message, 'requires');
    throw error;
  }
}

/** Every hook a requirement names is the owner's, and none already waits on `id` (as the server). */
async function checkRequirement(ownerId: string, id: string | null, text: string | null): Promise<string[]> {
  if (text === null) return [];
  const named = leavesOf(JSON.parse(text) as never);
  for (const leaf of named) await checkOwned(ownerId, leaf, liveHook, 'A requirement names a hook that isn’t one of yours', 'requires');
  if (id !== null) {
    const edges = await prisma.hookDependency.findMany({ where: { createdById: ownerId }, select: { parentHookId: true, childHookId: true } });
    if (named.some((leaf) => wouldCloseCycle(edges, leaf, id)))
      throw validationError('A hook can’t wait on itself or on a hook that waits on it', 'requires');
  }
  return named;
}

/** A hook with a requirement waits on exactly the hooks it names: its incoming edges follow. */
async function edgesFollow(ownerId: string, id: string, named: readonly string[], stamp: Date): Promise<void> {
  const have = await prisma.hookDependency.findMany({ where: { childHookId: id }, select: { id: true, parentHookId: true } });
  await prisma.$transaction([
    prisma.hookDependency.deleteMany({ where: { id: { in: have.filter((edge) => !named.includes(edge.parentHookId)).map((edge) => edge.id) } } }),
    ...named
      .filter((parent) => !have.some((edge) => edge.parentHookId === parent))
      .map((parent) =>
        prisma.hookDependency.create({
          data: { createdById: ownerId, parentHookId: parent, childHookId: id, reason: 'requirement', createdAt: stamp, updatedAt: stamp },
        }),
      ),
  ]);
}

export const hooks: ResourceSpec<HookRow, z.infer<typeof hookCreate>, z.infer<typeof hookUpdate>> = {
  resource: 'hook',
  plural: 'hooks',
  modelName: 'HookModel',
  createSchema: hookCreate,
  updateSchema: hookUpdate,
  list: (ownerId, query) =>
    prisma.hook.findMany({
      where: {
        createdById: ownerId,
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['setting_id', 'settingId'],
          ['canon_level', 'canonLevel'],
          ['kind', 'kind'],
          ['giver_person_id', 'giverPersonId'],
          ['giver_faction_id', 'giverFactionId'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.hook.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkHookRefs(ownerId, input);
    const requires = requirementText(input.requires);
    const named = await checkRequirement(ownerId, null, requires);
    const row = await prisma.hook.create({
      data: { createdById: ownerId, ...written(HOOK_COLUMNS, { ...input, requires }, stamp) } as Prisma.HookUncheckedCreateInput,
    });
    if (requires !== null) await edgesFollow(ownerId, row.id, named, stamp);
    return row;
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.hook.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true, isTemplate: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    checkTemplateStays(owner?.isTemplate ?? null, input.is_template);
    if (owner !== null) await checkHookRefs(owner.createdById, input);
    const changesRequirement = 'requires' in input;
    const requires = changesRequirement ? requirementText(input.requires) : null;
    const named = owner === null || !changesRequirement ? [] : await checkRequirement(owner.createdById, id, requires);
    const { count } = await prisma.hook.updateMany({
      where: { id, updatedAt: version },
      data: written(HOOK_COLUMNS, changesRequirement ? { ...input, requires } : input, stamp, userId) as Prisma.HookUncheckedUpdateManyInput,
    });
    if (count === 0) return null;
    if (owner !== null && changesRequirement) await edgesFollow(owner.createdById, id, named, stamp);
    return prisma.hook.findUnique({ where: { id } });
  },
  async remove(id) {
    // Its dependencies (either end) and everyone's progress go with it, as on the server.
    await prisma.$transaction([
      prisma.hookDependency.deleteMany({ where: { OR: [{ parentHookId: id }, { childHookId: id }] } }),
      prisma.personHook.deleteMany({ where: { hookId: id } }),
      prisma.factionHook.deleteMany({ where: { hookId: id } }),
      prisma.disposition.deleteMany({ where: { triggerHookId: id } }),
      prisma.relationInfluence.deleteMany({ where: { hookId: id } }),
      prisma.hook.update({ where: { id }, data: tombstone() }),
    ]);
  },
  fields: (row) => ({ ...fieldsOf(HOOK_COLUMNS, row), resolved_at: row.resolvedAt?.toISOString() ?? null }),
};

const DEPENDENCY_COLUMNS: Columns = {
  parent_hook_id: plain('parentHookId'),
  child_hook_id: plain('childHookId'),
  reason: plain('reason'),
};
const dependencyCreate = z.object({
  parent_hook_id: z.string().min(1),
  child_hook_id: z.string().min(1),
  reason: z.string().nullable().default(null),
});
const dependencyUpdate = z.object({ reason: z.string().nullable() }).partial();
type DependencyRow = Prisma.HookDependencyGetPayload<object>;

export const hookDependencies: ResourceSpec<DependencyRow, z.infer<typeof dependencyCreate>, z.infer<typeof dependencyUpdate>> = {
  resource: 'hook_dependency',
  plural: 'hook_dependencies',
  modelName: 'HookDependencyModel',
  createSchema: dependencyCreate,
  updateSchema: dependencyUpdate,
  list: (ownerId, query) =>
    prisma.hookDependency.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['parent_hook_id', 'parentHookId'],
          ['child_hook_id', 'childHookId'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.hookDependency.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkOwned(ownerId, input.parent_hook_id, liveHook, 'That hook is not one of yours', 'parent_hook_id');
    await checkOwned(ownerId, input.child_hook_id, liveHook, 'That hook is not one of yours', 'child_hook_id');
    const child = await prisma.hook.findUnique({ where: { id: input.child_hook_id }, select: { requires: true } });
    if (child?.requires) throw validationError('That hook’s requirement is an expression: edit it there', 'child_hook_id');
    const edges = await prisma.hookDependency.findMany({
      where: { createdById: ownerId },
      select: { parentHookId: true, childHookId: true },
    });
    if (wouldCloseCycle(edges, input.parent_hook_id, input.child_hook_id))
      throw validationError('A hook can’t wait on itself or on a hook that waits on it', 'child_hook_id');
    if (edges.some((one) => one.parentHookId === input.parent_hook_id && one.childHookId === input.child_hook_id))
      throw validationError('That dependency is already there', 'child_hook_id');
    return prisma.hookDependency.create({
      data: { createdById: ownerId, ...written(DEPENDENCY_COLUMNS, input, stamp) } as Prisma.HookDependencyUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.hookDependency.updateMany({
      where: { id, updatedAt: version },
      data: written(DEPENDENCY_COLUMNS, input, stamp, userId) as Prisma.HookDependencyUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.hookDependency.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.hookDependency.delete({ where: { id } });
  },
  fields: (row) => fieldsOf(DEPENDENCY_COLUMNS, row),
};

const progressFields = {
  status: z.string().max(LIMITS.hook_status_characters, `A status is at most ${LIMITS.hook_status_characters} characters`).nullable(),
  accepted_at: z.coerce.date().nullable(),
  completed_at: z.coerce.date().nullable(),
  progress: z.number().min(0, 'Progress is zero or more').nullable(),
};
const PROGRESS_COLUMNS: Columns = {
  status: plain('status'),
  accepted_at: plain('acceptedAt'),
  completed_at: plain('completedAt'),
  progress: plain('progress'),
};
const progressUpdate = z.object(progressFields).partial();
const isoOf = (row: { acceptedAt: Date | null; completedAt: Date | null }) => ({
  accepted_at: row.acceptedAt?.toISOString() ?? null,
  completed_at: row.completedAt?.toISOString() ?? null,
});

const PERSON_HOOK_COLUMNS: Columns = { person_id: plain('personId'), hook_id: plain('hookId'), ...PROGRESS_COLUMNS };
const personHookCreate = z.object({
  person_id: z.string().min(1),
  hook_id: z.string().min(1),
  status: progressFields.status.default(null),
  accepted_at: progressFields.accepted_at.default(null),
  completed_at: progressFields.completed_at.default(null),
  progress: progressFields.progress.default(null),
});
type PersonHookRow = Prisma.PersonHookGetPayload<object>;

export const personHooks: ResourceSpec<PersonHookRow, z.infer<typeof personHookCreate>, z.infer<typeof progressUpdate>> = {
  resource: 'person_hook',
  plural: 'person_hooks',
  modelName: 'PersonHookModel',
  createSchema: personHookCreate,
  updateSchema: progressUpdate,
  list: (ownerId, query) =>
    prisma.personHook.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['person_id', 'personId'],
          ['hook_id', 'hookId'],
          ['status', 'status'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.personHook.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkOwned(ownerId, input.person_id, livePerson, 'That person is not one of yours', 'person_id');
    await checkOwned(ownerId, input.hook_id, liveHook, 'That hook is not one of yours', 'hook_id');
    if ((await prisma.personHook.count({ where: { personId: input.person_id, hookId: input.hook_id } })) > 0)
      throw validationError('That one is already on this hook: update its progress instead', 'hook_id');
    return prisma.personHook.create({
      data: { createdById: ownerId, ...written(PERSON_HOOK_COLUMNS, input, stamp) } as Prisma.PersonHookUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.personHook.updateMany({
      where: { id, updatedAt: version },
      data: written(PROGRESS_COLUMNS, input, stamp, userId) as Prisma.PersonHookUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.personHook.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.personHook.delete({ where: { id } });
  },
  fields: (row) => ({ ...fieldsOf(PERSON_HOOK_COLUMNS, row), ...isoOf(row) }),
};

const FACTION_HOOK_COLUMNS: Columns = { faction_id: plain('factionId'), hook_id: plain('hookId'), ...PROGRESS_COLUMNS };
const factionHookCreate = personHookCreate.omit({ person_id: true }).extend({ faction_id: z.string().min(1) });
type FactionHookRow = Prisma.FactionHookGetPayload<object>;

export const factionHooks: ResourceSpec<FactionHookRow, z.infer<typeof factionHookCreate>, z.infer<typeof progressUpdate>> = {
  resource: 'faction_hook',
  plural: 'faction_hooks',
  modelName: 'FactionHookModel',
  createSchema: factionHookCreate,
  updateSchema: progressUpdate,
  list: (ownerId, query) =>
    prisma.factionHook.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['faction_id', 'factionId'],
          ['hook_id', 'hookId'],
          ['status', 'status'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.factionHook.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkOwned(ownerId, input.faction_id, liveFaction, 'That organisation is not one of yours', 'faction_id');
    await checkOwned(ownerId, input.hook_id, liveHook, 'That hook is not one of yours', 'hook_id');
    if ((await prisma.factionHook.count({ where: { factionId: input.faction_id, hookId: input.hook_id } })) > 0)
      throw validationError('That one is already on this hook: update its progress instead', 'hook_id');
    return prisma.factionHook.create({
      data: { createdById: ownerId, ...written(FACTION_HOOK_COLUMNS, input, stamp) } as Prisma.FactionHookUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.factionHook.updateMany({
      where: { id, updatedAt: version },
      data: written(PROGRESS_COLUMNS, input, stamp, userId) as Prisma.FactionHookUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.factionHook.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.factionHook.delete({ where: { id } });
  },
  fields: (row) => ({ ...fieldsOf(FACTION_HOOK_COLUMNS, row), ...isoOf(row) }),
};

// ---- taxon, entity_taxon, status, entity_status (W6) -----------------------------------------

const colour = z
  .string()
  .regex(/^#[0-9a-fA-F]{6}$/, 'A colour is # and six hex digits, like #a83232')
  .nullable();
const targetType = z.enum(ENTITY_TYPES as [string, ...string[]]);
const taxonParent: ParentOf = async (id) => (await prisma.taxon.findUnique({ where: { id }, select: { parentId: true } }))?.parentId ?? null;
const liveTaxon = (where: { id: string; createdById: string }) => prisma.taxon.count({ where: { ...where, deletedAt: null } });
const liveStatus = (where: { id: string; createdById: string }) => prisma.status.count({ where: { ...where, deletedAt: null } });

const TAXON_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  parent_id: plain('parentId'),
  kind: plain('kind'),
  colour: plain('colour'),
  campaign_id: plain('campaignId'),
  setting_id: plain('settingId'),
  canon_level: plain('canonLevel'),
};
const taxonFields = {
  name,
  description: z.string(),
  parent_id: reference,
  kind: kindOf(TAXON_KINDS),
  colour,
  campaign_id: reference,
  setting_id: reference,
  canon_level: canonLevel,
};
const taxonCreate = z.object({
  ...taxonFields,
  description: z.string().default(''),
  parent_id: reference.default(null),
  kind: kindOf(TAXON_KINDS).default(null),
  colour: colour.default(null),
  campaign_id: reference.default(null),
  setting_id: reference.default(null),
  canon_level: canonLevel.default(null),
});
const taxonUpdate = z.object(taxonFields).partial();
type TaxonRow = Prisma.TaxonGetPayload<object>;

async function checkTaxonRefs(ownerId: string, input: Record<string, unknown>): Promise<void> {
  await checkWorld(ownerId, input.campaign_id);
    await checkSetting(ownerId, input, null);
  await checkOwned(ownerId, input.parent_id, liveTaxon, 'That taxon is not one of yours', 'parent_id');
}

export const taxa: ResourceSpec<TaxonRow, z.infer<typeof taxonCreate>, z.infer<typeof taxonUpdate>> = {
  resource: 'taxon',
  plural: 'taxons',
  modelName: 'TaxonModel',
  createSchema: taxonCreate,
  updateSchema: taxonUpdate,
  list: (ownerId, query) =>
    prisma.taxon.findMany({
      where: {
        createdById: ownerId,
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['setting_id', 'settingId'],
          ['canon_level', 'canonLevel'],
          ['kind', 'kind'],
          ['parent_id', 'parentId'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.taxon.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkTaxonRefs(ownerId, input);
    return prisma.taxon.create({ data: { createdById: ownerId, ...written(TAXON_COLUMNS, input, stamp) } as Prisma.TaxonUncheckedCreateInput });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.taxon.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    if (owner !== null) await checkTaxonRefs(owner.createdById, input);
    await checkNoCycle(id, input.parent_id, taxonParent, 'taxon');
    const { count } = await prisma.taxon.updateMany({
      where: { id, updatedAt: version },
      data: written(TAXON_COLUMNS, input, stamp, userId) as Prisma.TaxonUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.taxon.findUnique({ where: { id } });
  },
  async remove(id) {
    // Taken off every record, as on the server.
    await prisma.$transaction([prisma.entityTaxon.deleteMany({ where: { taxonId: id } }), prisma.taxon.update({ where: { id }, data: tombstone() })]);
  },
  fields: (row) => fieldsOf(TAXON_COLUMNS, row),
};

const ENTITY_TAXON_COLUMNS: Columns = {
  taxon_id: plain('taxonId'),
  target_entity_type: plain('targetEntityType'),
  target_entity_id: plain('targetEntityId'),
};
const entityTaxonCreate = z.object({ taxon_id: z.string().min(1), target_entity_type: targetType, target_entity_id: z.string().min(1) });
const nothing = z.object({}).partial();
type EntityTaxonRow = Prisma.EntityTaxonGetPayload<object>;

export const entityTaxa: ResourceSpec<EntityTaxonRow, z.infer<typeof entityTaxonCreate>, z.infer<typeof nothing>> = {
  resource: 'entity_taxon',
  plural: 'entity_taxons',
  modelName: 'EntityTaxonModel',
  createSchema: entityTaxonCreate,
  updateSchema: nothing,
  list: (ownerId, query) =>
    prisma.entityTaxon.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['taxon_id', 'taxonId'],
          ['target_entity_type', 'targetEntityType'],
          ['target_entity_id', 'targetEntityId'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.entityTaxon.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkOwned(ownerId, input.taxon_id, liveTaxon, 'That taxon is not one of yours', 'taxon_id');
    const where = { taxonId: input.taxon_id, targetEntityType: input.target_entity_type, targetEntityId: input.target_entity_id };
    if ((await prisma.entityTaxon.count({ where })) > 0) throw validationError('That record already has that taxon', 'taxon_id');
    return prisma.entityTaxon.create({
      data: { createdById: ownerId, ...written(ENTITY_TAXON_COLUMNS, input, stamp) } as Prisma.EntityTaxonUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.entityTaxon.updateMany({
      where: { id, updatedAt: version },
      data: written(ENTITY_TAXON_COLUMNS, input, stamp, userId) as Prisma.EntityTaxonUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.entityTaxon.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.entityTaxon.delete({ where: { id } });
  },
  fields: (row) => fieldsOf(ENTITY_TAXON_COLUMNS, row),
};

const STATUS_COLUMNS: Columns = {
  name: plain('name'),
  description: plain('description'),
  kind: plain('kind'),
  colour: plain('colour'),
  campaign_id: plain('campaignId'),
  setting_id: plain('settingId'),
  canon_level: plain('canonLevel'),
};
const statusFields = { name, description: z.string(), kind: kindOf(STATUS_KINDS), colour, campaign_id: reference, setting_id: reference, canon_level: canonLevel };
const statusCreate = z.object({
  ...statusFields,
  description: z.string().default(''),
  kind: kindOf(STATUS_KINDS).default(null),
  colour: colour.default(null),
  campaign_id: reference.default(null),
  setting_id: reference.default(null),
  canon_level: canonLevel.default(null),
});
const statusUpdate = z.object(statusFields).partial();
type StatusRow = Prisma.StatusGetPayload<object>;

export const statuses: ResourceSpec<StatusRow, z.infer<typeof statusCreate>, z.infer<typeof statusUpdate>> = {
  resource: 'status',
  plural: 'statuses',
  modelName: 'StatusModel',
  createSchema: statusCreate,
  updateSchema: statusUpdate,
  list: (ownerId, query) =>
    prisma.status.findMany({
      where: {
        createdById: ownerId,
        deletedAt: null,
        ...filters(query, [
          ['campaign_id', 'campaignId'],
          ['setting_id', 'settingId'],
          ['canon_level', 'canonLevel'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { name: 'asc' },
    }),
  find: (id, ownerId) => prisma.status.findFirst({ where: { id, createdById: ownerId, deletedAt: null } }),
  async insert(ownerId, input, stamp) {
    await checkWorld(ownerId, input.campaign_id);
    await checkSetting(ownerId, input, null);
    return prisma.status.create({ data: { createdById: ownerId, ...written(STATUS_COLUMNS, input, stamp) } as Prisma.StatusUncheckedCreateInput });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.status.findUnique({ where: { id }, select: { createdById: true, campaignId: true, settingId: true } });
    checkWorldStays(owner?.campaignId, input.campaign_id);
    if (owner !== null) await checkSetting(owner.createdById, input, owner);
    if (owner !== null) await checkWorld(owner.createdById, input.campaign_id);
    const { count } = await prisma.status.updateMany({
      where: { id, updatedAt: version },
      data: written(STATUS_COLUMNS, input, stamp, userId) as Prisma.StatusUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.status.findUnique({ where: { id } });
  },
  async remove(id) {
    // Cleared from every record that had it, as on the server.
    await prisma.$transaction([prisma.entityStatus.deleteMany({ where: { statusId: id } }), prisma.status.update({ where: { id }, data: tombstone() })]);
  },
  fields: (row) => fieldsOf(STATUS_COLUMNS, row),
};

const ENTITY_STATUS_COLUMNS: Columns = {
  status_id: plain('statusId'),
  target_entity_type: plain('targetEntityType'),
  target_entity_id: plain('targetEntityId'),
};
const entityStatusCreate = z.object({ status_id: z.string().min(1), target_entity_type: targetType, target_entity_id: z.string().min(1) });
const entityStatusUpdate = z.object({ status_id: z.string().min(1) }).partial();
type EntityStatusRow = Prisma.EntityStatusGetPayload<object>;

export const entityStatuses: ResourceSpec<EntityStatusRow, z.infer<typeof entityStatusCreate>, z.infer<typeof entityStatusUpdate>> = {
  resource: 'entity_status',
  plural: 'entity_statuses',
  modelName: 'EntityStatusModel',
  createSchema: entityStatusCreate,
  updateSchema: entityStatusUpdate,
  list: (ownerId, query) =>
    prisma.entityStatus.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['status_id', 'statusId'],
          ['target_entity_type', 'targetEntityType'],
          ['target_entity_id', 'targetEntityId'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.entityStatus.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkOwned(ownerId, input.status_id, liveStatus, 'That status is not one of yours', 'status_id');
    if ((await prisma.entityStatus.count({ where: { targetEntityType: input.target_entity_type, targetEntityId: input.target_entity_id } })) > 0)
      throw validationError('That record already has a status: change it instead', 'status_id');
    return prisma.entityStatus.create({
      data: { createdById: ownerId, ...written(ENTITY_STATUS_COLUMNS, input, stamp) } as Prisma.EntityStatusUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const owner = await prisma.entityStatus.findUnique({ where: { id }, select: { createdById: true } });
    if (owner !== null) await checkOwned(owner.createdById, input.status_id, liveStatus, 'That status is not one of yours', 'status_id');
    const { count } = await prisma.entityStatus.updateMany({
      where: { id, updatedAt: version },
      data: written(ENTITY_STATUS_COLUMNS, input, stamp, userId) as Prisma.EntityStatusUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.entityStatus.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.entityStatus.delete({ where: { id } });
  },
  fields: (row) => fieldsOf(ENTITY_STATUS_COLUMNS, row),
};

// ---- relationship (W5: people and organisations, attitude, colour, mirror) --------------------

const RELATION_COLUMNS: Columns = {
  person_id: plain('personId'),
  faction_id: plain('factionId'),
  target_person_id: plain('targetPersonId'),
  target_faction_id: plain('targetFactionId'),
  kind: plain('kind'),
  discriminator: plain('discriminator'),
  intensity: plain('intensity'),
  qualifier: plain('qualifier'),
  valid_from: plain('validFrom'),
  valid_to: plain('validTo'),
  notes: plain('notes'),
  colour: plain('colour'),
  mirror_relationship_id: plain('mirrorRelationshipId'),
};
/** What a mirror shares with its relation; the ends are swapped, not shared (as the server's MIRRORED). */
const MIRRORED = ['kind', 'discriminator', 'intensity', 'qualifier', 'valid_from', 'valid_to', 'notes', 'colour'] as const;
const sharedFields = {
  kind: z.string().nullable(),
  discriminator: z.string().nullable(),
  intensity: z.number().min(-1, 'Attitude is -1 to +1').max(1, 'Attitude is -1 to +1').nullable(),
  qualifier: z.string().nullable(),
  valid_from: z.coerce.date().nullable(),
  valid_to: z.coerce.date().nullable(),
  notes: z.string().nullable(),
  colour,
};
const relationCreate = z.object({
  person_id: reference.default(null),
  faction_id: reference.default(null),
  target_person_id: reference.default(null),
  target_faction_id: reference.default(null),
  kind: sharedFields.kind.default(null),
  discriminator: sharedFields.discriminator.default(null),
  intensity: sharedFields.intensity.default(null),
  qualifier: sharedFields.qualifier.default(null),
  valid_from: sharedFields.valid_from.default(null),
  valid_to: sharedFields.valid_to.default(null),
  notes: sharedFields.notes.default(null),
  colour: colour.default(null),
  mirror_relationship_id: reference.default(null),
});
const relationUpdate = z.object(sharedFields).partial();
type RelationRow = Prisma.RelationshipGetPayload<object>;

async function checkRelationEnds(ownerId: string, input: z.infer<typeof relationCreate>): Promise<void> {
  const one = (a: string | null, b: string | null) => (a === null) !== (b === null);
  if (!one(input.person_id, input.faction_id) || !one(input.target_person_id, input.target_faction_id))
    throw validationError('Each side of a relation is one person or one organisation', 'target_person_id');
  if (input.faction_id !== null && input.faction_id === input.target_faction_id)
    throw validationError('A relation needs two different organisations', 'target_faction_id');
  for (const [field, value] of [
    ['person_id', input.person_id],
    ['target_person_id', input.target_person_id],
  ] as const)
    await checkOwned(ownerId, value, livePerson, 'That person is not one of yours', field);
  for (const [field, value] of [
    ['faction_id', input.faction_id],
    ['target_faction_id', input.target_faction_id],
  ] as const)
    await checkOwned(ownerId, value, liveFaction, 'That organisation is not one of yours', field);
  if (input.mirror_relationship_id === null) return;
  const other = await prisma.relationship.findFirst({ where: { id: input.mirror_relationship_id, createdById: ownerId } });
  if (other === null) throw validationError('That mirror relation is not one of yours', 'mirror_relationship_id');
  const swapped =
    other.personId === input.target_person_id &&
    other.targetPersonId === input.person_id &&
    other.factionId === input.target_faction_id &&
    other.targetFactionId === input.faction_id;
  if (!swapped) throw validationError('A mirror has the same two ends, the other way round', 'mirror_relationship_id');
  if (other.mirrorRelationshipId !== null) throw validationError('That relation already has a mirror', 'mirror_relationship_id');
}

export const relationships: ResourceSpec<RelationRow, z.infer<typeof relationCreate>, z.infer<typeof relationUpdate>> = {
  resource: 'relationship',
  plural: 'relationships',
  modelName: 'RelationshipModel',
  createSchema: relationCreate,
  updateSchema: relationUpdate,
  list: (ownerId, query) =>
    prisma.relationship.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['person_id', 'personId'],
          ['faction_id', 'factionId'],
          ['target_person_id', 'targetPersonId'],
          ['target_faction_id', 'targetFactionId'],
          ['kind', 'kind'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.relationship.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkRelationEnds(ownerId, input);
    const row = await prisma.relationship.create({
      data: { createdById: ownerId, ...written(RELATION_COLUMNS, input, stamp) } as Prisma.RelationshipUncheckedCreateInput,
    });
    if (input.mirror_relationship_id !== null)
      await prisma.relationship.update({ where: { id: input.mirror_relationship_id }, data: { mirrorRelationshipId: row.id, updatedAt: stamp } });
    return row;
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const data = written(RELATION_COLUMNS, input, stamp, userId) as Prisma.RelationshipUncheckedUpdateManyInput;
    const { count } = await prisma.relationship.updateMany({ where: { id, updatedAt: version }, data });
    if (count === 0) return null;
    const row = await prisma.relationship.findUnique({ where: { id } });
    if (row?.mirrorRelationshipId) {
      const shared = Object.fromEntries(MIRRORED.filter((field) => field in input).map((field) => [field, input[field]]));
      if (Object.keys(shared).length > 0)
        await prisma.relationship.update({ where: { id: row.mirrorRelationshipId }, data: written(RELATION_COLUMNS, shared, stamp, userId) });
    }
    return row;
  },
  async remove(id) {
    // A relation takes its mirror and its influences with it, as on the server.
    await prisma.$transaction([
      prisma.relationInfluence.deleteMany({ where: { relationshipId: id } }),
      prisma.relationship.deleteMany({ where: { OR: [{ id }, { mirrorRelationshipId: id }] } }),
    ]);
  },
  fields: (row) => ({
    ...fieldsOf(RELATION_COLUMNS, row),
    valid_from: row.validFrom?.toISOString() ?? null,
    valid_to: row.validTo?.toISOString() ?? null,
  }),
};

// ---- disposition, relation_influence (W56: narrative state from dh-campaign's tracker) --------

const attitude = z
  .string()
  .refine((value) => ATTITUDES.includes(value) || value in ATTITUDE_NUANCES, 'An attitude is one from the scale, or a nuance of one');
const DISPOSITION_COLUMNS: Columns = {
  person_id: plain('personId'),
  target_kind: plain('targetKind'),
  target_person_id: plain('targetPersonId'),
  target_faction_id: plain('targetFactionId'),
  attitude: plain('attitude'),
  is_default: plain('isDefault'),
  trigger_hook_id: plain('triggerHookId'),
  note: plain('note'),
};
const dispositionCreate = z
  .object({
    person_id: z.string().min(1),
    target_kind: z.enum(DISPOSITION_TARGETS as [string, ...string[]]),
    target_person_id: reference.default(null),
    target_faction_id: reference.default(null),
    attitude,
    is_default: z.boolean().default(false),
    trigger_hook_id: reference.default(null),
    note: z.string().nullable().default(null),
  })
  .refine(
    (input) =>
      (input.target_kind === 'party' && input.target_person_id === null && input.target_faction_id === null) ||
      (input.target_kind === 'person' && input.target_person_id !== null && input.target_faction_id === null) ||
      (input.target_kind === 'faction' && input.target_faction_id !== null && input.target_person_id === null),
    { message: 'Name the target that matches target_kind: a person, an organisation, or neither for the party', path: ['target_kind'] },
  )
  .refine((input) => input.is_default !== (input.trigger_hook_id !== null), {
    message: 'An entry is either the default or has a trigger hook',
    path: ['trigger_hook_id'],
  });
const dispositionUpdate = z.object({ attitude, note: z.string().nullable() }).partial();
type DispositionRow = Prisma.DispositionGetPayload<object>;

export const dispositions: ResourceSpec<DispositionRow, z.infer<typeof dispositionCreate>, z.infer<typeof dispositionUpdate>> = {
  resource: 'disposition',
  plural: 'dispositions',
  modelName: 'DispositionModel',
  createSchema: dispositionCreate,
  updateSchema: dispositionUpdate,
  list: (ownerId, query) =>
    prisma.disposition.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['person_id', 'personId'],
          ['target_kind', 'targetKind'],
          ['target_person_id', 'targetPersonId'],
          ['target_faction_id', 'targetFactionId'],
          ['trigger_hook_id', 'triggerHookId'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.disposition.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkOwned(ownerId, input.person_id, livePerson, 'That person is not one of yours', 'person_id');
    await checkOwned(ownerId, input.target_person_id, livePerson, 'That person is not one of yours', 'target_person_id');
    await checkOwned(ownerId, input.target_faction_id, liveFaction, 'That organisation is not one of yours', 'target_faction_id');
    await checkOwned(ownerId, input.trigger_hook_id, liveHook, 'That hook is not one of yours', 'trigger_hook_id');
    if (input.is_default) {
      const same = {
        personId: input.person_id,
        targetKind: input.target_kind,
        targetPersonId: input.target_person_id,
        targetFactionId: input.target_faction_id,
        isDefault: true,
      };
      if ((await prisma.disposition.count({ where: same })) > 0)
        throw validationError('That person already has a default attitude toward that target', 'is_default');
    }
    return prisma.disposition.create({
      data: { createdById: ownerId, ...written(DISPOSITION_COLUMNS, input, stamp) } as Prisma.DispositionUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.disposition.updateMany({
      where: { id, updatedAt: version },
      data: written(DISPOSITION_COLUMNS, input, stamp, userId) as Prisma.DispositionUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.disposition.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.disposition.delete({ where: { id } });
  },
  fields: (row) => fieldsOf(DISPOSITION_COLUMNS, row),
};

const INFLUENCE_COLUMNS: Columns = {
  relationship_id: plain('relationshipId'),
  hook_id: plain('hookId'),
  to_intensity: plain('toIntensity'),
  note: plain('note'),
};
const toIntensity = z.number().min(-1, 'Attitude is -1 to +1').max(1, 'Attitude is -1 to +1');
const influenceCreate = z.object({
  relationship_id: z.string().min(1),
  hook_id: z.string().min(1),
  to_intensity: toIntensity,
  note: z.string().nullable().default(null),
});
const influenceUpdate = z.object({ to_intensity: toIntensity, note: z.string().nullable() }).partial();
type InfluenceRow = Prisma.RelationInfluenceGetPayload<object>;

export const relationInfluences: ResourceSpec<InfluenceRow, z.infer<typeof influenceCreate>, z.infer<typeof influenceUpdate>> = {
  resource: 'relation_influence',
  plural: 'relation_influences',
  modelName: 'RelationInfluenceModel',
  createSchema: influenceCreate,
  updateSchema: influenceUpdate,
  list: (ownerId, query) =>
    prisma.relationInfluence.findMany({
      where: {
        createdById: ownerId,
        ...filters(query, [
          ['relationship_id', 'relationshipId'],
          ['hook_id', 'hookId'],
        ]),
      },
      orderBy: { createdAt: 'asc' },
    }),
  find: (id, ownerId) => prisma.relationInfluence.findFirst({ where: { id, createdById: ownerId } }),
  async insert(ownerId, input, stamp) {
    await checkOwned(ownerId, input.relationship_id, (where) => prisma.relationship.count({ where }), 'That relation is not one of yours', 'relationship_id');
    await checkOwned(ownerId, input.hook_id, liveHook, 'That hook is not one of yours', 'hook_id');
    return prisma.relationInfluence.create({
      data: { createdById: ownerId, ...written(INFLUENCE_COLUMNS, input, stamp) } as Prisma.RelationInfluenceUncheckedCreateInput,
    });
  },
  async updateIfCurrent(id, version, input, stamp, userId) {
    const { count } = await prisma.relationInfluence.updateMany({
      where: { id, updatedAt: version },
      data: written(INFLUENCE_COLUMNS, input, stamp, userId) as Prisma.RelationInfluenceUncheckedUpdateManyInput,
    });
    return count === 0 ? null : prisma.relationInfluence.findUnique({ where: { id } });
  },
  async remove(id) {
    await prisma.relationInfluence.delete({ where: { id } });
  },
  fields: (row) => fieldsOf(INFLUENCE_COLUMNS, row),
};
