// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * The records the UI reads and writes, through the framework client: the same calls whichever back
 * end answers. Every change is guarded by the version the person saw (If-Match), so a stale one
 * surfaces as a conflict, never a silent overwrite.
 *
 * `resource`, `jsonBody`, `Fields` and `ResourceHooks` are zephyrex-rpg-ai's
 * (client/src/features/data/records.ts), copied as they stand: the second copy, flagged for the
 * framework with columns.ts.
 */
import useSWR, { type SWRResponse, useSWRConfig } from 'swr';
import { useClient } from 'zephyrex';
import { z } from 'zod';
import {
  ENTITY_TYPES,
  TAGGABLE_TYPES,
  FACTION_KINDS,
  HOOK_KINDS,
  ITEM_KINDS,
  JOURNAL_KINDS,
  LOCATION_KINDS,
  PERSON_KINDS,
  POST_POSITIONS,
  STATUS_KINDS,
  TAXON_KINDS,
} from '../../contract';

const JSON_BODY = z.json();

/** A record's id: one function for every list, so hooks keyed on it (useHidden) stay stable. */
export const idOf = (record: { id: string }): string => record.id;

/**
 * A request body as the JSON the wire carries (fields left undefined are dropped). Typed form
 * fields hold `unknown` in places, which JSON alone can vouch for.
 */
export function jsonBody(value: unknown): z.infer<typeof JSON_BODY> {
  return JSON_BODY.parse(JSON.parse(JSON.stringify(value)) as unknown);
}

const versioned = { id: z.string(), created_at: z.string(), updated_at: z.string().nullable() };
const kindIn = (kinds: readonly string[]) => z.enum(kinds as [string, ...string[]]).nullable();

export const worldSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  setting_id: z.string().nullish(),
  /** Where the scenario came from: homebrew, official or adapted, and its source. */
  provenance: z.string().nullish(),
  source: z.string().nullish(),
  /** Copy on start: a scenario is never played; a playthrough names the scenario it was copied from. */
  is_scenario: z.boolean().nullish(),
  scenario_id: z.string().nullish(),
});
export type World = z.infer<typeof worldSchema>;

/** A setting (S6): the universe campaigns take place in; its campaign-less records are its canon. */
export const settingSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  slug: z.string().nullish(),
});
export type Setting = z.infer<typeof settingSchema>;

export const placeSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  entry: z.string().nullable(),
  kind: kindIn(LOCATION_KINDS),
  parent_id: z.string().nullable(),
  campaign_id: z.string().nullable(),
  associated_person_id: z.string().nullable(),
  /** A template (S4b, W7): copied into worlds, never a world fact. */
  is_template: z.boolean().nullish(),
  /** S4c: other names it goes by, and what else wakes it in the AI's lorebook (JSON text). */
  aliases: z.string().nullish(),
  keywords: z.string().nullish(),
  /** S4d: its lorebook activation (JSON text). */
  lore: z.string().nullish(),
  /** Where it came from: homebrew, official or adapted, and its source. */
  provenance: z.string().nullish(),
  source: z.string().nullish(),
  /** Its picture by https link (shown with no referrer). */
  picture_url: z.string().nullish(),
});
export type Place = z.infer<typeof placeSchema>;

export const personSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  entry: z.string().nullable(),
  kind: kindIn(PERSON_KINDS),
  campaign_id: z.string().nullable(),
  location_id: z.string().nullable(),
  /** A template (S4b, W7): copied into worlds, never a world fact. */
  is_template: z.boolean().nullish(),
  /** S4c: other names it goes by, and what else wakes it in the AI's lorebook (JSON text). */
  aliases: z.string().nullish(),
  keywords: z.string().nullish(),
  /** S4d: its lorebook activation (JSON text). */
  lore: z.string().nullish(),
  /** Where it came from: homebrew, official or adapted, and its source. */
  provenance: z.string().nullish(),
  source: z.string().nullish(),
  /** Its picture by https link (shown with no referrer). */
  picture_url: z.string().nullish(),
  /** S4c: how the AI plays them (JSON text); for the GM. */
  voice: z.string().nullish(),
});
export type Person = z.infer<typeof personSchema>;

export const factionSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  entry: z.string().nullable(),
  kind: kindIn(FACTION_KINDS),
  parent_id: z.string().nullable(),
  campaign_id: z.string().nullable(),
  /** A template (S4b, W7): copied into worlds, never a world fact. */
  is_template: z.boolean().nullish(),
  /** S4c: other names it goes by, and what else wakes it in the AI's lorebook (JSON text). */
  aliases: z.string().nullish(),
  keywords: z.string().nullish(),
  /** S4d: its lorebook activation (JSON text). */
  lore: z.string().nullish(),
  /** Where it came from: homebrew, official or adapted, and its source. */
  provenance: z.string().nullish(),
  source: z.string().nullish(),
  /** Its picture by https link (shown with no referrer). */
  picture_url: z.string().nullish(),
});
export type Faction = z.infer<typeof factionSchema>;

export const itemSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  entry: z.string().nullable(),
  kind: kindIn(ITEM_KINDS),
  weight: z.number().nullable(),
  base_value: z.number().nullable(),
  stack_size: z.number().nullable(),
  campaign_id: z.string().nullable(),
  /** A template (S4b, W7): copied into worlds, never a world fact. */
  is_template: z.boolean().nullish(),
  /** S4c: other names it goes by, and what else wakes it in the AI's lorebook (JSON text). */
  aliases: z.string().nullish(),
  keywords: z.string().nullish(),
  /** S4d: its lorebook activation (JSON text). */
  lore: z.string().nullish(),
  /** Where it came from: homebrew, official or adapted, and its source. */
  provenance: z.string().nullish(),
  source: z.string().nullish(),
  /** Its picture by https link (shown with no referrer). */
  picture_url: z.string().nullish(),
});
export type Item = z.infer<typeof itemSchema>;

export const itemInstanceSchema = z.object({
  ...versioned,
  item_id: z.string().nullable(),
  location_id: z.string().nullable(),
  owner_person_id: z.string().nullable(),
  quantity: z.number().nullable(),
  durability: z.number().nullable(),
});
export type ItemInstance = z.infer<typeof itemInstanceSchema>;

export const carriedSchema = z.object({
  ...versioned,
  target_entity_type: z.enum(ENTITY_TYPES as [string, ...string[]]),
  target_entity_id: z.string(),
  item_instance_id: z.string().nullable(),
  quantity: z.number().nullable(),
});
export type Carried = z.infer<typeof carriedSchema>;

export const journalSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  entry: z.string().nullable(),
  kind: kindIn(JOURNAL_KINDS),
  location_id: z.string().nullable(),
  author_person_id: z.string().nullable(),
  session_number: z.number().nullable(),
  occurred_at: z.string().nullable(),
  campaign_id: z.string().nullable(),
  /** A template (S4b, W7): copied into worlds, never a world fact. */
  is_template: z.boolean().nullish(),
  /** S4c: other names it goes by, and what else wakes it in the AI's lorebook (JSON text). */
  aliases: z.string().nullish(),
  keywords: z.string().nullish(),
  /** S4d: its lorebook activation (JSON text). */
  lore: z.string().nullish(),
  /** Where it came from: homebrew, official or adapted, and its source. */
  provenance: z.string().nullish(),
  source: z.string().nullish(),
  /** Its picture by https link (shown with no referrer). */
  picture_url: z.string().nullish(),
});
export type Journal = z.infer<typeof journalSchema>;

export const postSchema = z.object({
  ...versioned,
  target_entity_type: z.enum(ENTITY_TYPES as [string, ...string[]]),
  target_entity_id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  entry: z.string().nullable(),
  position: z.enum(POST_POSITIONS as [string, ...string[]]).nullable(),
  ordinal: z.number().nullable(),
});
export type Post = z.infer<typeof postSchema>;

export const hookSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  entry: z.string().nullable(),
  kind: kindIn(HOOK_KINDS),
  giver_person_id: z.string().nullable(),
  giver_faction_id: z.string().nullable(),
  requires: z.string().nullable(),
  excuse: z.string().nullable(),
  resolved_at: z.string().nullable(),
  resolved_journal_id: z.string().nullable(),
  campaign_id: z.string().nullable(),
  /** A template (S4b, W7): copied into worlds, never a world fact. */
  is_template: z.boolean().nullish(),
  /** S4c: other names it goes by, and what else wakes it in the AI's lorebook (JSON text). */
  aliases: z.string().nullish(),
  keywords: z.string().nullish(),
  /** S4d: its lorebook activation (JSON text). */
  lore: z.string().nullish(),
  /** Where it came from: homebrew, official or adapted, and its source. */
  provenance: z.string().nullish(),
  source: z.string().nullish(),
  /** Its picture by https link (shown with no referrer). */
  picture_url: z.string().nullish(),
});
export type Hook = z.infer<typeof hookSchema>;

export const hookDependencySchema = z.object({
  ...versioned,
  parent_hook_id: z.string(),
  child_hook_id: z.string(),
  reason: z.string().nullable(),
});
export type HookDependency = z.infer<typeof hookDependencySchema>;

const progress = {
  hook_id: z.string(),
  status: z.string().nullable(),
  accepted_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  progress: z.number().nullable(),
};
export const personHookSchema = z.object({ ...versioned, person_id: z.string(), ...progress });
export type PersonHook = z.infer<typeof personHookSchema>;
export const factionHookSchema = z.object({ ...versioned, faction_id: z.string(), ...progress });
export type FactionHook = z.infer<typeof factionHookSchema>;

export const taxonSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  parent_id: z.string().nullable(),
  kind: kindIn(TAXON_KINDS),
  colour: z.string().nullable(),
  campaign_id: z.string().nullable(),
});
export type Taxon = z.infer<typeof taxonSchema>;

const target = { target_entity_type: z.enum(ENTITY_TYPES as [string, ...string[]]), target_entity_id: z.string() };
// A taxon tags any record, and a campaign too (a scenario's play styles).
export const entityTaxonSchema = z.object({ ...versioned, taxon_id: z.string(), target_entity_type: z.enum(TAGGABLE_TYPES as [string, ...string[]]), target_entity_id: z.string() });
export type EntityTaxon = z.infer<typeof entityTaxonSchema>;

export const statusSchema = z.object({
  ...versioned,
  name: z.string(),
  description: z.string().nullable(),
  kind: kindIn(STATUS_KINDS),
  colour: z.string().nullable(),
  campaign_id: z.string().nullable(),
});
export type Status = z.infer<typeof statusSchema>;

export const entityStatusSchema = z.object({ ...versioned, status_id: z.string(), ...target });
export type EntityStatus = z.infer<typeof entityStatusSchema>;

export const relationshipSchema = z.object({
  ...versioned,
  person_id: z.string().nullable(),
  faction_id: z.string().nullable(),
  target_person_id: z.string().nullable(),
  target_faction_id: z.string().nullable(),
  kind: z.string().nullable(),
  discriminator: z.string().nullable(),
  intensity: z.number().nullable(),
  qualifier: z.string().nullable(),
  notes: z.string().nullable(),
  colour: z.string().nullable(),
  mirror_relationship_id: z.string().nullable(),
});
export type Relationship = z.infer<typeof relationshipSchema>;

export const dispositionSchema = z.object({
  ...versioned,
  person_id: z.string(),
  target_kind: z.string(),
  target_person_id: z.string().nullable(),
  target_faction_id: z.string().nullable(),
  attitude: z.string(),
  is_default: z.boolean().nullable(),
  trigger_hook_id: z.string().nullable(),
  note: z.string().nullable(),
});
export type Disposition = z.infer<typeof dispositionSchema>;

export const relationInfluenceSchema = z.object({
  ...versioned,
  relationship_id: z.string(),
  hook_id: z.string(),
  to_intensity: z.number(),
  note: z.string().nullable(),
});
export type RelationInfluence = z.infer<typeof relationInfluenceSchema>;

type Versioned = { id: string; created_at: string; updated_at: string | null };
/** What a write may set: a record's own fields (and, for write-only fields, `Extra`). */
export type Fields<T extends Versioned, Extra = object> = Partial<Omit<T, keyof Versioned>> & Extra;

/** The record a single-record answer wraps (`{ <resource>: {...} }`). */
function one<T>(schema: z.ZodType<T>, key: string, body: unknown): T {
  return schema.parse(z.record(z.string(), z.unknown()).parse(body)[key]);
}

export interface ResourceHooks<T extends Versioned, Create, Extra> {
  path: string;
  /** The records, read only while `enabled` (by default, always). */
  useList(query?: Record<string, string>, enabled?: boolean): SWRResponse<T[], Error>;
  useOne(id: string | null): SWRResponse<T, Error>;
  useActions(): {
    create(fields: Create): Promise<T>;
    update(seen: T, changes: Fields<T, Extra>): Promise<T>;
    remove(seen: T): Promise<void>;
  };
}

/** A resource's hooks, from its singular name, plural and schema. */
export function resource<T extends Versioned, Create extends object, Extra = object>(
  singular: string,
  plural: string,
  schema: z.ZodType<T>,
): ResourceHooks<T, Create, Extra> {
  const path = `/v1/${singular}`;
  const listKey = (query?: Record<string, string>) =>
    query === undefined || Object.keys(query).length === 0 ? path : `${path}?${new URLSearchParams(query).toString()}`;
  return {
    path,
    useList(query, enabled = true) {
      const client = useClient();
      const key = listKey(query);
      // The filter goes to client.list as params, never in the path: list adds its own
      // ?offset=&limit=, so a path with a query would get a second `?` (and an empty list).
      return useSWR(enabled ? key : null, () => client.list(path, plural, schema, query ?? {}));
    },
    useOne(id) {
      const client = useClient();
      return useSWR(id === null ? null : `${path}/${id}`, async () =>
        one(schema, singular, await client.get(`${path}/${id ?? ''}`)),
      );
    },
    useActions() {
      const client = useClient();
      const { mutate } = useSWRConfig();
      // A change has every list of this resource, and the record itself, read again.
      const refresh = async (id?: string) => {
        await mutate(
          (key) => typeof key === 'string' && (key === path || key.startsWith(`${path}?`) || key === `${path}/${id ?? ''}`),
        );
      };
      return {
        async create(fields) {
          const saved = one(schema, singular, await client.post(path, jsonBody({ [singular]: fields })));
          await refresh(saved.id);
          return saved;
        },
        async update(seen, changes) {
          const saved = one(
            schema,
            singular,
            await client.put(`${path}/${seen.id}`, jsonBody({ [singular]: changes }), seen),
          );
          await refresh(saved.id);
          return saved;
        },
        async remove(seen) {
          await client.delete(`${path}/${seen.id}`, seen);
          await refresh(seen.id);
        },
      };
    },
  };
}

export const worlds = resource<World, Fields<World> & { name: string }>('campaign', 'campaigns', worldSchema);
export const settings = resource<Setting, Fields<Setting> & { name: string }>('setting', 'settings', settingSchema);
export const places = resource<Place, Fields<Place, { entry?: unknown }> & { name: string }>(
  'location',
  'locations',
  placeSchema,
);
export const people = resource<Person, Fields<Person, { entry?: unknown }> & { name: string }>(
  'person',
  'persons',
  personSchema,
);
export const factions = resource<Faction, Fields<Faction, { entry?: unknown }> & { name: string }>(
  'faction',
  'factions',
  factionSchema,
);
export const items = resource<Item, Fields<Item, { entry?: unknown }> & { name: string }>('item', 'items', itemSchema);
export const itemInstances = resource<ItemInstance, Fields<ItemInstance>>('item_instance', 'item_instances', itemInstanceSchema);
export const carried = resource<
  Carried,
  Pick<Carried, 'target_entity_type' | 'target_entity_id' | 'item_instance_id'> & Fields<Carried>
>('entity_inventory', 'entity_inventories', carriedSchema);
export const journals = resource<Journal, Fields<Journal, { entry?: unknown }> & { name: string }>(
  'journal',
  'journals',
  journalSchema,
);
export const posts = resource<
  Post,
  Pick<Post, 'target_entity_type' | 'target_entity_id' | 'name'> & Fields<Post, { entry?: unknown }>
>('entity_post', 'entity_posts', postSchema);
export const hooks = resource<Hook, Fields<Hook, { entry?: unknown }> & { name: string }>('hook', 'hooks', hookSchema);
export const hookDependencies = resource<HookDependency, Pick<HookDependency, 'parent_hook_id' | 'child_hook_id'> & Fields<HookDependency>>(
  'hook_dependency',
  'hook_dependencies',
  hookDependencySchema,
);
export const personHooks = resource<PersonHook, Pick<PersonHook, 'person_id' | 'hook_id'> & Fields<PersonHook>>(
  'person_hook',
  'person_hooks',
  personHookSchema,
);
export const factionHooks = resource<FactionHook, Pick<FactionHook, 'faction_id' | 'hook_id'> & Fields<FactionHook>>(
  'faction_hook',
  'faction_hooks',
  factionHookSchema,
);
export const taxa = resource<Taxon, Fields<Taxon> & { name: string }>('taxon', 'taxons', taxonSchema);
export const entityTaxa = resource<EntityTaxon, Pick<EntityTaxon, 'taxon_id' | 'target_entity_type' | 'target_entity_id'>>(
  'entity_taxon',
  'entity_taxons',
  entityTaxonSchema,
);
export const statuses = resource<Status, Fields<Status> & { name: string }>('status', 'statuses', statusSchema);
export const entityStatuses = resource<EntityStatus, Pick<EntityStatus, 'status_id' | 'target_entity_type' | 'target_entity_id'>>(
  'entity_status',
  'entity_statuses',
  entityStatusSchema,
);
export const relationships = resource<Relationship, Fields<Relationship>>('relationship', 'relationships', relationshipSchema);
export const dispositions = resource<
  Disposition,
  Pick<Disposition, 'person_id' | 'target_kind' | 'attitude'> & Fields<Disposition>
>('disposition', 'dispositions', dispositionSchema);
export const relationInfluences = resource<
  RelationInfluence,
  Pick<RelationInfluence, 'relationship_id' | 'hook_id' | 'to_intensity'> & Fields<RelationInfluence>
>('relation_influence', 'relation_influences', relationInfluenceSchema);
