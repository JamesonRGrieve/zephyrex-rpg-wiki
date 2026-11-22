// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it, vi } from 'vitest';
import { afterInstantiate, onAfterInstantiate } from './afterInstantiate';

describe('after a lite start', () => {
  it('calls each callback in order with the ids, passes over a failing one, and unregisters', async () => {
    const heard: string[] = [];
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const offBroken = onAfterInstantiate(() => {
      throw new Error("the frame's copy failed");
    });
    const offListening = onAfterInstantiate(async ({ sourceCampaignId, newCampaignId, idMap }) => {
      heard.push(`${sourceCampaignId}→${newCampaignId} ${idMap.inn ?? ''}`);
      await Promise.resolve();
    });
    const started = { ownerId: 'o', sourceCampaignId: 's1', newCampaignId: 'run1', idMap: { s1: 'run1', inn: 'inn2' } };
    await afterInstantiate(started);
    expect(heard).toEqual(['s1→run1 inn2']);
    expect(warn).toHaveBeenCalledOnce();
    offBroken();
    offListening();
    await afterInstantiate(started);
    expect(heard).toHaveLength(1);
    warn.mockRestore();
  });
});
