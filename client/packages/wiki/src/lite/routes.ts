// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The wiki's lite API (/v1/<resource> and /v1/<resource>/<id>, as the SaaS server answers them)
 * behind one catch-all route: `app/api/v1/[...wiki]/route.lite.ts` in the app that serves it,
 *
 *   export const { GET, POST, PUT, PATCH, DELETE } = wikiLite({ prisma });
 *
 * Next serves an app's own specific routes before the catch-all, so an app's /v1/extension,
 * session_report or anything else it answers itself wins. Its schema carries the wiki's fragment
 * (prisma/wiki.prisma, scripts/prisma-fragment.mjs).
 */
import { campaignCardPersonPost } from './cardPerson';
import { campaignLoreSearchPost } from './loreSearch';
import type { PrismaClient } from '@prisma/client';
import { apiErrorResponse, collectionRoutes, localOwner, notFound, recordRoutes, type RecordRow, type ResourceSpec } from '@zephyrex/lite';
import type { NextRequest, NextResponse } from 'next/server';
import { bindPrisma } from './db';
import { metadataDelete, metadataOfGet, metadataPatch, metadataPost } from './recordMetadataRoutes';
import { campaignDocumentsGet } from './campaignDocuments';
import { campaignElevatePost, campaignFillPersonPost } from './authoredNpcs';
import { campaignFramingGet } from './campaignFraming';
import { campaignPersonPost } from './ensurePerson';
import { settingPregensGet } from './pregens';
import { campaignInstantiatePost, campaignStartGet } from './scenarios';
import { clockGet, clockPost, personMovePost, personMovesGet } from './worldTick';
import { sessionReportGet, sessionReportPost } from './sessionReportRoutes';
import { worldEntityGet, campaignMatchingPost } from './worldEntityRoute';
import {
  campaigns,
  dispositions,
  knownFacts,
  entityInventories,
  entityPosts,
  entityStatuses,
  entityTaxa,
  factionHooks,
  factions,
  hookDependencies,
  hooks,
  itemInstances,
  items,
  journals,
  locations,
  people,
  personHooks,
  propertyKits,
  relationInfluences,
  relationships,
  settings,
  statuses,
  taxa,
} from './worldRecords';

type Context = { params: Promise<Record<string, string>> };
type Handler = (request: NextRequest, context: Context) => Promise<NextResponse>;
type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
type Methods = Partial<Record<Method, Handler>>;

/**
 * A resource's routes: /v1/<resource>, /v1/<resource>/<id>, and its named actions,
 * /v1/<resource>/<action> (matched before an id: record_metadata/of) and
 * /v1/<resource>/<id>/<action> (property_kit/<id>/apply).
 */
type Routes = { collection: Methods; record: Methods; actions?: Record<string, Methods>; recordActions?: Record<string, Methods> };

/** A resource's list and create, and its read, update and delete, as @zephyrex/lite answers them. */
function both<Row extends RecordRow, Create, Update>(spec: ResourceSpec<Row, Create, Update>): Routes {
  return { collection: collectionRoutes(spec, localOwner), record: recordRoutes(spec, localOwner) };
}

/** Every resource the catch-all answers, by its path. */
const ROUTES: Record<string, Routes> = {
  // Copy on start: POST /v1/campaign/{id}/instantiate.
  campaign: {
    ...both(campaigns),
    actions: { card_person: { POST: campaignCardPersonPost } },
    recordActions: { instantiate: { POST: campaignInstantiatePost }, clock: { GET: clockGet, POST: clockPost }, person: { POST: campaignPersonPost }, framing: { GET: campaignFramingGet }, fill_person: { POST: campaignFillPersonPost }, elevate: { POST: campaignElevatePost }, matching: { POST: campaignMatchingPost }, lore_search: { POST: campaignLoreSearchPost } },
  },
  // The world tick: people moved by the GM, each move kept.
  person_move: { collection: { GET: personMovesGet, POST: personMovePost }, record: {} },
  // A start's progress and result (lite's starts are done when answered).
  campaign_start: { collection: {}, record: { GET: campaignStartGet } },
  disposition: both(dispositions),
  known_fact: both(knownFacts),
  entity_inventory: both(entityInventories),
  entity_post: both(entityPosts),
  entity_status: both(entityStatuses),
  entity_taxon: both(entityTaxa),
  faction: both(factions),
  faction_hook: both(factionHooks),
  hook: both(hooks),
  hook_dependency: both(hookDependencies),
  item: both(items),
  item_instance: both(itemInstances),
  journal: both(journals),
  location: both(locations),
  person: both(people),
  person_hook: both(personHooks),
  property_kit: both(propertyKits),
  relation_influence: both(relationInfluences),
  relationship: both(relationships),
  // A setting's pregenerated player characters (GET /v1/setting/{id}/pregen).
  setting: { ...both(settings), recordActions: { pregen: { GET: settingPregensGet } } },
  status: both(statuses),
  taxon: both(taxa),
  world_entity: { collection: { GET: worldEntityGet }, record: {} },
  // Parity's data bank: a campaign's records' full text.
  campaign_document: { collection: { GET: campaignDocumentsGet }, record: {} },
  session_report: { collection: { POST: sessionReportPost }, record: { GET: sessionReportGet } },
  // The framework's metadata extension, as the wiki's lite records need it (S4b).
  record_metadata: { collection: { POST: metadataPost }, record: { PATCH: metadataPatch, DELETE: metadataDelete }, actions: { of: { GET: metadataOfGet } } },
};

const own = <T>(table: Record<string, T> | undefined, key: string | undefined): T | undefined =>
  // Own keys only: "constructor" and the like are not routes.
  table !== undefined && key !== undefined && Object.hasOwn(table, key) ? table[key] : undefined;

/** The handler for a path under /v1, and the id it names, if any. */
function routed(path: readonly string[], method: Method): { handler: Handler | undefined; id: string | undefined } {
  const [resource, second, third, ...rest] = path;
  const route = own(ROUTES, resource);
  if (route === undefined || rest.length > 0) return { handler: undefined, id: undefined };
  if (second === undefined) return { handler: route.collection[method], id: undefined };
  if (third !== undefined) return { handler: own(route.recordActions, third)?.[method], id: second };
  const action = own(route.actions, second);
  return action !== undefined ? { handler: action[method], id: undefined } : { handler: route.record[method], id: second };
}

/** The resource paths the catch-all answers. */
export const WIKI_LITE_RESOURCES: readonly string[] = Object.keys(ROUTES);

export interface WikiLiteOptions {
  /** The app's Prisma client; its schema includes prisma/wiki.prisma. */
  prisma: PrismaClient;
}

type CatchAll = (request: NextRequest, context: { params: Promise<{ wiki?: string[] }> }) => Promise<NextResponse>;

export function wikiLite({ prisma }: WikiLiteOptions): Record<Method, CatchAll> {
  bindPrisma(prisma);
  const answer =
    (method: Method): CatchAll =>
    async (request, context) => {
      const path = (await context.params).wiki ?? [];
      const { handler, id } = routed(path, method);
      if (handler === undefined) return apiErrorResponse(notFound(path[0] ?? 'Resource'));
      const params: Record<string, string> = id === undefined ? {} : { id };
      return handler(request, { params: Promise.resolve(params) });
    };
  return { GET: answer('GET'), POST: answer('POST'), PUT: answer('PUT'), PATCH: answer('PATCH'), DELETE: answer('DELETE') };
}
