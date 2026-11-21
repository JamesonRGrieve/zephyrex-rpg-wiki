// SPDX-License-Identifier: AGPL-3.0-or-later
/** Copy on start: POST /v1/campaign/{id}/instantiate, a playthrough of a scenario (both editions). */
import { useCallback } from 'react';
import { useSWRConfig } from 'swr';
import { useClient } from 'zephyrex';
import { z } from 'zod';
import { worldSchema } from './records';

const started = z.object({ campaign: worldSchema, id_map: z.record(z.string(), z.string()) });
export type Started = z.infer<typeof started>;

/** Starts the scenario: its new playthrough and the map of each copied record's id to its copy's. */
export function useStartScenario(): (scenarioId: string, name?: string) => Promise<Started> {
  const client = useClient();
  const { mutate } = useSWRConfig();
  return useCallback(
    async (scenarioId: string, name?: string): Promise<Started> => {
      const made = started.parse(await client.post(`/v1/campaign/${encodeURIComponent(scenarioId)}/instantiate`, { instantiate: name ? { name } : {} }));
      // Every list of worlds shows the new one.
      await mutate((key) => typeof key === 'string' && key.startsWith('/v1/campaign'));
      return made;
    },
    [client, mutate],
  );
}
