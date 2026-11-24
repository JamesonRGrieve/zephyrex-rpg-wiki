// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * Reads of just the rows a page names, never a campaign's whole lists (operator, 2026-11-24: a record
 * page "took forever" opening in rpg-ai's drawer on a 970-record campaign, reading every person,
 * organisation, item, hook and link to name a few). Each is one request (world_entity?ids=, or the
 * LIST `<field>__in` filter both back ends take) and one SWR entry keyed by its ids, so panels
 * naming the same rows share it.
 */
import useSWR, { type SWRResponse } from 'swr';
import { useClient } from 'zephyrex';
import { z } from 'zod';
import { MAX_IDS } from '../../lib/entityIds';

/** A named world record as GET /v1/world_entity?ids= answers it (both editions). */
export const namedSchema = z.object({ id: z.string(), kind: z.string(), name: z.string(), gm_only: z.boolean().nullish() });
export type Named = z.infer<typeof namedSchema>;

/** What a by-id read needs of a resource (every one in records.ts has it). */
export interface RowSource<T> {
  path: string;
  single: string;
  plural: string;
  schema: z.ZodType<T>;
}

const sorted = (ids: readonly (string | null | undefined)[]): string[] =>
  [...new Set(ids.filter((id): id is string => typeof id === 'string' && id !== ''))].sort();

/**
 * The places, people, organisations, items and journals named by `ids`, by id, in one request per
 * MAX_IDS (world_entity?ids=: wherever they are, under the reader's access, each with gm_only). An id
 * the reader can't see is absent.
 */
export function useNamed(ids: readonly (string | null | undefined)[]): SWRResponse<Map<string, Named>, Error> {
  const client = useClient();
  const wanted = sorted(ids);
  return useSWR(wanted.length === 0 ? null : `/v1/world_entity?ids=${wanted.join(',')}`, async () => {
    const found = new Map<string, Named>();
    for (let start = 0; start < wanted.length; start += MAX_IDS) {
      const body = z
        .object({ world_entities: z.array(namedSchema) })
        .parse(await client.get('/v1/world_entity', { ids: wanted.slice(start, start + MAX_IDS).join(',') }));
      for (const one of body.world_entities) found.set(one.id, one);
    }
    return found;
  });
}

/** At most this many values one `<field>__in` takes (the framework's MAX_BATCH_SIZE). */
const MAX_IN = 100;

/** The rows of `resource` whose `field` is any of `values`: one `<field>__in` list per MAX_IN values. */
async function listIn<T>(client: ReturnType<typeof useClient>, resource: RowSource<T>, field: string, values: readonly string[]): Promise<T[]> {
  const rows: T[] = [];
  for (let start = 0; start < values.length; start += MAX_IN) {
    rows.push(...(await client.list(resource.path, resource.plural, resource.schema, { [`${field}__in`]: values.slice(start, start + MAX_IN).join(',') })));
  }
  return rows;
}

/** The rows of `resource` with these ids, by id, in one request (id__in); one gone or not the reader's is absent. */
export function useRowsById<T extends { id: string }>(resource: RowSource<T>, ids: readonly (string | null | undefined)[]): SWRResponse<Map<string, T>, Error> {
  const client = useClient();
  const wanted = sorted(ids);
  return useSWR(wanted.length === 0 ? null : `${resource.path}?id__in=${wanted.join(',')}`, async () => {
    const found = new Map<string, T>();
    for (const row of await listIn(client, resource, 'id', wanted)) found.set(row.id, row);
    return found;
  });
}

/** The rows of `resource` whose `field` is one of `values`, in one request (`<field>__in`). */
export function useRowsWhere<T extends { id: string }>(
  resource: RowSource<T>,
  field: string,
  values: readonly (string | null | undefined)[],
): SWRResponse<T[], Error> {
  const client = useClient();
  const wanted = sorted(values);
  return useSWR(wanted.length === 0 ? null : `${resource.path}?${field}__in=${wanted.join(',')}`, async () => listIn(client, resource, field, wanted));
}
