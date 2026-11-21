// SPDX-License-Identifier: AGPL-3.0-or-later
// A start answers 202 and runs on: the hook follows it to the end, reporting progress, and returns
// the playthrough; a failed start is an error with its reason.
import { renderHook } from '@testing-library/react';
import { SWRConfig } from 'swr';
import { createElement, type ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

const RUN = { id: 'run 1', created_at: '2026-11-21T00:00:00', updated_at: null, name: 'Run 1', description: null, setting_id: null, is_scenario: false, scenario_id: 's1' };
const client = { get: vi.fn(), post: vi.fn() };
vi.mock('zephyrex', () => ({ useClient: () => client }));

const wrapper = ({ children }: { children: ReactNode }) => createElement(SWRConfig, { value: { provider: () => new Map() } }, children);

describe('starting a scenario', () => {
  it('follows a running start to its playthrough, reporting each step', async () => {
    const { useStartScenario } = await import('./scenarios');
    client.post.mockResolvedValueOnce({ start: { id: 'st1', scenario_id: 's1', campaign_id: null, state: 'running', done: 0, total: 13, step: 'copying tags' } });
    client.get
      .mockResolvedValueOnce({ campaign_start: { id: 'st1', state: 'running', done: 4, total: 13, step: 'copying people', campaign_id: 'run 1' } })
      .mockResolvedValueOnce({ campaign_start: { id: 'st1', state: 'done', done: 13, total: 13, step: 'done', campaign_id: 'run 1', id_map: '{"s1":"run 1"}' } })
      .mockResolvedValueOnce({ campaign: RUN });
    const steps: string[] = [];
    const { result } = renderHook(() => useStartScenario(), { wrapper });
    const started = await result.current('s1', 'Run 1', (start) => steps.push(`${start.done ?? 0}/${start.total ?? 0} ${start.step ?? ''}`));
    expect(started.campaign.id).toBe('run 1');
    expect(started.id_map).toEqual({ s1: 'run 1' });
    expect(steps).toEqual(['0/13 copying tags', '4/13 copying people', '13/13 done']);
    expect(client.post).toHaveBeenCalledWith('/v1/campaign/s1/instantiate', { instantiate: { name: 'Run 1' } });
    expect(client.get).toHaveBeenCalledWith('/v1/campaign_start/st1');
  });

  it('fails with the start’s reason', async () => {
    const { useStartScenario } = await import('./scenarios');
    client.post.mockResolvedValueOnce({ start: { id: 'st2', state: 'failed', error: 'Attach one asset at a time' } });
    const { result } = renderHook(() => useStartScenario(), { wrapper });
    await expect(result.current('s1')).rejects.toThrow('Attach one asset at a time');
  });
});
