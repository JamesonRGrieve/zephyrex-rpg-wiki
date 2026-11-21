// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Copy on start: POST /v1/campaign/{id}/instantiate answers 202 with a start, and the copy runs in
 * the background (operator, 2026-11-21: "make it async with the progress bar and auto load it when
 * it's done"); GET /v1/campaign_start/{id} reports its progress, then the playthrough (both editions).
 */
import { useCallback } from 'react';
import { useSWRConfig } from 'swr';
import { useClient } from 'zephyrex';
import { z } from 'zod';
import { worldSchema } from './records';

export const startSchema = z.object({
  id: z.string(),
  scenario_id: z.string().nullish(),
  campaign_id: z.string().nullish(),
  state: z.enum(['running', 'done', 'failed']),
  done: z.number().nullish(),
  total: z.number().nullish(),
  step: z.string().nullish(),
  id_map: z.string().nullish(),
  error: z.string().nullish(),
});
export type Start = z.infer<typeof startSchema>;
export type Started = { campaign: z.infer<typeof worldSchema>; id_map: Record<string, string> };

const accepted = z.object({ start: startSchema });
const polled = z.object({ campaign_start: startSchema });
const fetched = z.object({ campaign: worldSchema });
/** How often a running start is asked after. */
export const POLL_MS = 500;

const wait = (ms: number): Promise<void> =>
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  });

/** Starts the scenario and follows it to the end: its new playthrough and the map of each copied
 * record's id to its copy's. ``onProgress`` hears each report while it runs. */
export function useStartScenario(): (scenarioId: string, name?: string, onProgress?: (start: Start) => void) => Promise<Started> {
  const client = useClient();
  const { mutate } = useSWRConfig();
  return useCallback(
    async (scenarioId: string, name?: string, onProgress?: (start: Start) => void): Promise<Started> => {
      let start = accepted.parse(await client.post(`/v1/campaign/${encodeURIComponent(scenarioId)}/instantiate`, { instantiate: name ? { name } : {} })).start;
      onProgress?.(start);
      while (start.state === 'running') {
        // eslint-disable-next-line no-await-in-loop -- one report at a time, until it ends
        await wait(POLL_MS);
        // eslint-disable-next-line no-await-in-loop
        start = polled.parse(await client.get(`/v1/campaign_start/${encodeURIComponent(start.id)}`)).campaign_start;
        onProgress?.(start);
      }
      if (start.state === 'failed' || !start.campaign_id) throw new Error(start.error ?? 'The scenario could not be started');
      const { campaign } = fetched.parse(await client.get(`/v1/campaign/${encodeURIComponent(start.campaign_id)}`));
      // Every list of worlds shows the new one.
      await mutate((key) => typeof key === 'string' && key.startsWith('/v1/campaign'));
      return { campaign, id_map: JSON.parse(start.id_map ?? '{}') as Record<string, string> };
    },
    [client, mutate],
  );
}
