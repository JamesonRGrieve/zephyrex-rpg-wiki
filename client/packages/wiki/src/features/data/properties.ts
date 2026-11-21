// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * A record's properties (S4b): its own key/values, the framework's /v1/record_metadata (the lite
 * edition answers the same paths). Read in order; added, changed and removed by the record's editors.
 */
import { useCallback } from 'react';
import useSWR, { type SWRResponse } from 'swr';
import { useClient } from 'zephyrex';
import { z } from 'zod';

export const propertySchema = z.object({
  id: z.string(),
  key: z.string(),
  value: z.string().nullable(),
  value_type: z.string().nullable(),
  ordinal: z.number(),
  is_private: z.boolean(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
});
export type Property = z.infer<typeof propertySchema>;

const OF = '/v1/record_metadata/of';
const BASE = '/v1/record_metadata';
const one = z.object({ record_metadata: propertySchema });

/** The record's properties, in order. */
export function useProperties(type: string, id: string): SWRResponse<Property[], Error> {
  const client = useClient();
  const params = { target_entity_type: type, target_entity_id: id };
  return useSWR<Property[], Error>(client.url(OF, params), async () => z.object({ metadata: z.array(propertySchema) }).parse(await client.get(OF, params)).metadata);
}

export interface PropertyActions {
  add: (key: string, valueType: string, ordinal: number) => Promise<Property>;
  save: (row: Property, value: string) => Promise<Property>;
  remove: (row: Property) => Promise<void>;
}

/** The writes to a record's properties; the caller refreshes the list after each. */
export function usePropertyActions(type: string, id: string): PropertyActions {
  const client = useClient();
  const add = useCallback(
    async (key: string, valueType: string, ordinal: number): Promise<Property> =>
      one.parse(await client.post(BASE, { record_metadata: { target_entity_type: type, target_entity_id: id, key, value_type: valueType, ordinal } }))
        .record_metadata,
    [client, type, id],
  );
  const save = useCallback(
    async (row: Property, value: string): Promise<Property> =>
      one.parse(await client.patch(`${BASE}/${encodeURIComponent(row.id)}`, { record_metadata: { value } }, row)).record_metadata,
    [client],
  );
  const remove = useCallback(
    async (row: Property): Promise<void> => {
      await client.delete(`${BASE}/${encodeURIComponent(row.id)}`, row);
    },
    [client],
  );
  return { add, save, remove };
}
