// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The wiki's lite API (/v1/<resource> and /v1/<resource>/<id>, as the SaaS server answers them)
 * behind one catch-all route: `app/api/v1/[...wiki]/route.lite.ts` in the app that serves it,
 *
 *   export const { GET, POST, PUT, DELETE } = wikiLite({ prisma });
 *
 * Next serves an app's own specific routes before the catch-all, so an app's /v1/extension,
 * session_report or anything else it answers itself wins. Its schema carries the wiki's fragment
 * (prisma/wiki.prisma, scripts/prisma-fragment.mjs).
 */
import type { PrismaClient } from '@prisma/client';
import { apiErrorResponse, collectionRoutes, localOwner, notFound, recordRoutes, type RecordRow, type ResourceSpec } from '@zephyrex/lite';
import type { NextRequest, NextResponse } from 'next/server';
import { bindPrisma } from './db';
import { sessionReportGet, sessionReportPost } from './sessionReportRoutes';
import { worldEntityGet } from './worldEntityRoute';
import {
  campaigns,
  dispositions,
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
type Methods = Partial<Record<'GET' | 'POST' | 'PUT' | 'DELETE', Handler>>;

type Routes = { collection: Methods; record: Methods };

/** A resource's list and create, and its read, update and delete, as @zephyrex/lite answers them. */
function both<Row extends RecordRow, Create, Update>(spec: ResourceSpec<Row, Create, Update>): Routes {
  return { collection: collectionRoutes(spec, localOwner), record: recordRoutes(spec, localOwner) };
}

/** Every resource the catch-all answers, by its path. */
const ROUTES: Record<string, Routes> = {
  campaign: both(campaigns),
  disposition: both(dispositions),
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
  setting: both(settings),
  status: both(statuses),
  taxon: both(taxa),
  world_entity: { collection: { GET: worldEntityGet }, record: {} },
  session_report: { collection: { POST: sessionReportPost }, record: { GET: sessionReportGet } },
};

/** The resource paths the catch-all answers. */
export const WIKI_LITE_RESOURCES: readonly string[] = Object.keys(ROUTES);

export interface WikiLiteOptions {
  /** The app's Prisma client; its schema includes prisma/wiki.prisma. */
  prisma: PrismaClient;
}

export function wikiLite({ prisma }: WikiLiteOptions): Record<'GET' | 'POST' | 'PUT' | 'DELETE', (request: NextRequest, context: { params: Promise<{ wiki?: string[] }> }) => Promise<NextResponse>> {
  bindPrisma(prisma);
  const answer =
    (method: 'GET' | 'POST' | 'PUT' | 'DELETE') =>
    async (request: NextRequest, context: { params: Promise<{ wiki?: string[] }> }): Promise<NextResponse> => {
      const [resource, id, ...rest] = (await context.params).wiki ?? [];
      // Own keys only: "constructor" and the like are not resources.
      const route = resource !== undefined && Object.hasOwn(ROUTES, resource) ? ROUTES[resource] : undefined;
      const handler = rest.length > 0 || route === undefined ? undefined : (id === undefined ? route.collection : route.record)[method];
      if (handler === undefined) return apiErrorResponse(notFound(resource ?? 'Resource'));
      const params: Record<string, string> = id === undefined ? {} : { id };
      return handler(request, { params: Promise.resolve(params) });
    };
  return { GET: answer('GET'), POST: answer('POST'), PUT: answer('PUT'), DELETE: answer('DELETE') };
}
