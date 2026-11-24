// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The wiki's back end for its stories (never compiled into dist): one setting with its canon, one
 * campaign in it, and the records a campaign holds, served by the framework's mock REST routes
 * (`restTable`) for every resource in features/data/records.ts, plus `GET /v1/extension`. The
 * content is original placeholder text. Each call makes a fresh store, so a story's writes never
 * reach another story.
 */
import { http, HttpResponse, type RequestHandler } from 'msw';
import { z } from 'zod';
import { restTable, serverExtensions } from 'zephyrex/testing/msw';
import {
  carried,
  dispositions,
  entityStatuses,
  entityTaxa,
  factionHooks,
  factions,
  hookDependencies,
  hooks,
  itemInstances,
  items,
  journals,
  knownFacts,
  people,
  personHooks,
  places,
  posts,
  relationInfluences,
  relationships,
  type ResourceHooks,
  settings,
  statuses,
  taxa,
  worlds,
} from '../features/data/records';
import { settingScope } from '../lib/scope';

/** Every server extension the wiki's pages read (capabilities.ts), as a full SaaS back end lists them. */
export const ALL_EXTENSIONS = [
  'rpg_core',
  'world_spatial',
  'genealogy',
  'world_social',
  'world_inventory',
  'world_narrative',
  'world_taxonomy',
  'entity_posts',
  'metadata',
  'world_properties',
] as const;

export const SETTING_ID = 'setting-1';
export const CAMPAIGN_ID = 'campaign-1';
/** A playthrough of the fixture's scenario (campaign-2). */
export const PLAYTHROUGH_ID = 'campaign-3';
/** The setting's own pages' scope (its canon). */
export const SETTING_SCOPE = settingScope(SETTING_ID);

const STAMP = '2026-11-20T12:00:00.000000';
type Row = { id: string };
type Fixture = Record<string, readonly Record<string, unknown>[]>;

/** The fixture world, by resource (its `single`): only the fields that matter; the rest are null. */
export function wikiFixture(): Fixture {
  return {
    setting: [{ id: SETTING_ID, name: 'Reality', slug: 'reality', description: 'The world as it is, in any era.' }],
    campaign: [
      { id: CAMPAIGN_ID, name: 'Harbour Lights', setting_id: SETTING_ID, description: 'A small port town and the storm that cut it off.' },
      { id: 'campaign-2', name: 'The Quiet Valley', setting_id: SETTING_ID, description: 'A scenario: a valley that went silent overnight.', is_scenario: true },
      { id: PLAYTHROUGH_ID, name: 'The Quiet Valley, first run', setting_id: SETTING_ID, description: 'A playthrough of the scenario.', scenario_id: 'campaign-2' },
    ],
    location: [
      { id: 'location-1', name: 'Saltmarsh Bay', kind: 'region', campaign_id: CAMPAIGN_ID, description: 'A bay of mudflats and fog.' },
      { id: 'location-2', name: 'Port Wren', kind: 'city', parent_id: 'location-1', campaign_id: CAMPAIGN_ID, description: 'The only town on the bay.' },
      { id: 'location-3', name: 'The Lantern House', kind: 'building', parent_id: 'location-2', campaign_id: CAMPAIGN_ID, description: 'An inn by the harbour wall.' },
      { id: 'location-4', name: 'The Old Lighthouse', kind: 'building', setting_id: SETTING_ID, description: 'Canon: dark for twenty years.' },
    ],
    person: [
      {
        id: 'person-1',
        name: 'Mara Quill',
        kind: 'npc',
        campaign_id: CAMPAIGN_ID,
        location_id: 'location-3',
        description: 'Keeps the Lantern House.',
        keywords: JSON.stringify(['innkeeper']),
        entry: JSON.stringify([
          { type: 'p', children: [{ text: 'Keeps the Lantern House.' }] },
          { type: 'h2', children: [{ text: 'GM secrets' }] },
          { type: 'p', children: [{ text: 'She lit the lighthouse herself.' }] },
        ]),
      },
      { id: 'person-2', name: 'Tobin Reyes', kind: 'pc', campaign_id: CAMPAIGN_ID, location_id: 'location-2', description: 'A ferryman stranded by the storm.' },
      { id: 'person-3', name: 'Harbourmaster Vell', kind: 'npc', campaign_id: CAMPAIGN_ID, description: 'Holds the keys to every boat.' },
      { id: 'person-4', name: 'Old Wick', kind: 'npc', campaign_id: 'campaign-2', description: 'The last shepherd in the valley.' },
      { id: 'person-5', name: 'Old Wick', kind: 'npc', campaign_id: PLAYTHROUGH_ID, description: 'Copied in at start.' },
      { id: 'person-6', name: 'New Face', kind: 'npc', campaign_id: PLAYTHROUGH_ID, description: 'Made in play.' },
    ],
    faction: [{ id: 'faction-1', name: 'The Harbour Guild', kind: 'guild', campaign_id: CAMPAIGN_ID, description: 'Fishers and boat owners.' }],
    item: [{ id: 'item-1', name: 'Brass Lantern', kind: 'misc', campaign_id: CAMPAIGN_ID, description: 'Never quite goes out.' }],
    journal: [
      { id: 'journal-1', name: 'Session 1: The storm', kind: 'session_report', session_number: 1, campaign_id: CAMPAIGN_ID, description: 'The ferry was the last boat in.' },
    ],
    hook: [
      { id: 'hook-1', name: 'Who lit the lighthouse?', kind: 'mystery', giver_person_id: 'person-1', campaign_id: CAMPAIGN_ID, description: 'A light shone from the old lighthouse.' },
      { id: 'hook-2', name: 'Reach the lighthouse', kind: 'objective', campaign_id: CAMPAIGN_ID, description: 'Cross the flats at low tide.' },
    ],
    hook_dependency: [{ id: 'hook_dependency-1', parent_hook_id: 'hook-2', child_hook_id: 'hook-1' }],
    taxon: [
      { id: 'taxon-1', name: 'Coastal', kind: 'tag', campaign_id: CAMPAIGN_ID },
      { id: 'taxon-2', name: 'Mystery', kind: 'play_style' },
    ],
    entity_taxon: [{ id: 'entity_taxon-1', taxon_id: 'taxon-1', target_entity_type: 'location', target_entity_id: 'location-1' }],
    status: [],
    entity_status: [],
    relationship: [
      { id: 'relationship-1', person_id: 'person-1', target_person_id: 'person-3', kind: 'rival', intensity: -0.4, notes: 'Argue over the harbour dues.' },
    ],
    disposition: [],
    relation_influence: [],
    person_hook: [],
    faction_hook: [],
    item_instance: [],
    entity_inventory: [],
    entity_post: [],
    known_fact: [{ id: 'known_fact-1', person_id: 'person-2', target_entity_type: 'person', target_entity_id: 'person-1', text: 'Mara keeps the lamp oil in the cellar.', campaign_id: CAMPAIGN_ID }],
  };
}

/** Every resource the pages read, each served at its own path. */
const RESOURCES: readonly ResourceHooks<Row & { created_at: string; updated_at: string | null }, object, object>[] = [
  worlds,
  settings,
  places,
  people,
  factions,
  items,
  itemInstances,
  carried,
  journals,
  posts,
  hooks,
  hookDependencies,
  personHooks,
  factionHooks,
  taxa,
  entityTaxa,
  statuses,
  entityStatuses,
  relationships,
  dispositions,
  relationInfluences,
  knownFacts,
] as unknown as readonly ResourceHooks<Row & { created_at: string; updated_at: string | null }, object, object>[];

/**
 * A fixture row as the server sends it: versioned, every field the schema has and the row doesn't
 * set as null, checked against the schema, and kept whole (a field the UI's schema doesn't read,
 * such as a place's setting_id, is still there for a list's filter, as on the server).
 */
function served(schema: z.ZodType, fields: Record<string, unknown>): Record<string, unknown> {
  const blank = schema instanceof z.ZodObject ? Object.fromEntries(Object.keys(schema.shape).map((key) => [key, null])) : {};
  const row = { ...blank, created_at: STAMP, updated_at: STAMP, ...fields };
  schema.parse(row);
  return row;
}

/**
 * The wiki's back end: `extensions` listed (all by default, so every panel shows), the fixture's
 * rows (any resource replaced by `rows`), and `extra` handlers first (a story's own answers).
 */
export function wikiHandlers({
  extensions = ALL_EXTENSIONS,
  rows = {},
  extra = [],
  gmOnly = [],
  properties = {},
}: {
  extensions?: readonly string[];
  rows?: Fixture;
  extra?: RequestHandler[];
  /** Records kept to the GM (their "GM only" property), by id. */
  gmOnly?: readonly string[];
  /** A record's properties, by its id: key, value and whether private. */
  properties?: Record<string, readonly { key: string; value: string; is_private?: boolean }[]>;
} = {}): RequestHandler[] {
  const fixture = { ...wikiFixture(), ...rows };
  // GET /v1/world_entity?ids=: the named places, people, organisations, items and journals, each
  // with gm_only (as both back ends answer it).
  const named = http.get('*/v1/world_entity', ({ request }) => {
    const ids = new Set((new URL(request.url).searchParams.get('ids') ?? '').split(',').filter(Boolean));
    const world_entities = (['location', 'person', 'faction', 'item', 'journal'] as const).flatMap((kind) =>
      (fixture[kind] ?? [])
        .filter((row) => ids.has(String(row.id)))
        .map((row) => ({ id: String(row.id), kind, name: String(row.name), gm_only: gmOnly.includes(String(row.id)) })),
    );
    return HttpResponse.json({ world_entities, next: null });
  });
  const metadata = http.get('*/v1/record_metadata/of', ({ request }) => {
    const id = new URL(request.url).searchParams.get('target_entity_id') ?? '';
    const own = [...(properties[id] ?? []), ...(gmOnly.includes(id) ? [{ key: 'GM only', value: 'true', is_private: true }] : [])];
    return HttpResponse.json({
      metadata: own.map((one, ordinal) => ({
        id: `record_metadata-${id}-${String(ordinal)}`,
        key: one.key,
        value: one.value,
        value_type: 'text',
        ordinal,
        is_private: one.is_private ?? false,
        created_at: STAMP,
        updated_at: STAMP,
      })),
    });
  });
  const tables = RESOURCES.flatMap((resource) => {
    let stored = (fixture[resource.single] ?? []).map((fields) => served(resource.schema, fields)) as (Row & {
      created_at: string;
      updated_at: string | null;
    })[];
    const filters = [...new Set(stored.flatMap((row) => Object.keys(row)))] as (keyof (typeof stored)[number] & string)[];
    // `<field>__in=a,b` (the framework's LIST filter, and the wiki's lite twin): restTable reads only
    // equality, so a list naming one is answered here, and every other falls through to it.
    const listedIn = http.get(`*${resource.path}`, ({ request }) => {
      const query = new URL(request.url).searchParams;
      const ins = [...query.keys()].filter((key) => key.endsWith('__in'));
      if (ins.length === 0) return undefined;
      const rows = stored.filter((row) =>
        ins.every((key) => (query.get(key) ?? '').split(',').includes(String((row as Record<string, unknown>)[key.slice(0, -4)]))),
      );
      return HttpResponse.json({ [resource.plural]: rows });
    });
    return [listedIn, ...restTable({
      rows: () => stored,
      set: (next) => {
        stored = next;
      },
      schema: resource.schema,
      endpoint: resource.path,
      single: resource.single,
      plural: resource.plural,
      filters,
    })];
  });
  return [
    ...extra,
    serverExtensions(...extensions),
    named,
    metadata,
    ...tables,
  ];
}
