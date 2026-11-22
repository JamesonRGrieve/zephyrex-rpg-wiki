// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Copy on start: POST /v1/campaign/{id}/instantiate answers 202 with a start, and the copy runs in
 * the background (operator, 2026-11-21: "make it async with the progress bar and auto load it when
 * it's done"); GET /v1/campaign_start/{id} reports its progress, then the playthrough (both editions).
 */
import { useCallback } from 'react';
import useSWR, { useSWRConfig } from 'swr';
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
export function useStartScenario(): (scenarioId: string, name?: string, onProgress?: (start: Start) => void, pregens?: readonly string[]) => Promise<Started> {
  const client = useClient();
  const { mutate } = useSWRConfig();
  return useCallback(
    async (scenarioId: string, name?: string, onProgress?: (start: Start) => void, pregens?: readonly string[]): Promise<Started> => {
      const instantiate = { ...(name ? { name } : {}), ...(pregens && pregens.length > 0 ? { pregens } : {}) };
      let start = accepted.parse(await client.post(`/v1/campaign/${encodeURIComponent(scenarioId)}/instantiate`, { instantiate })).start;
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

export const pregenSchema = z.object({
  id: z.string(),
  name: z.string(),
  summary: z.string(),
  picture_url: z.string().nullish(),
  tags: z.array(z.string()),
  source: z.string().nullish(),
});
export type Pregen = z.infer<typeof pregenSchema>;

/** A setting's pregenerated player characters, to pick from at a start (GET /v1/setting/{id}/pregen). */
export function usePregens(settingId: string | null | undefined): { data: Pregen[] | undefined; error: Error | undefined } {
  const client = useClient();
  const path = settingId ? `/v1/setting/${encodeURIComponent(settingId)}/pregen` : null;
  const { data, error } = useSWR<Pregen[], Error>(path, async () => z.object({ pregens: z.array(pregenSchema) }).parse(await client.get(path ?? '')).pregens);
  return { data, error };
}
