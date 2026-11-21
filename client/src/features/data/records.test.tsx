// SPDX-License-Identifier: AGPL-3.0-or-later
// A list's filter reaches the client as params, not in the path (the client adds its own
// ?offset=&limit=; a path with a query got a second `?` and every filtered list came back empty).
import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const list = vi.fn().mockResolvedValue([]);
vi.mock('zephyrex', () => ({ useClient: () => ({ list }) }));

describe('resource useList', () => {
  it('passes the filter as params and keeps the path clean', async () => {
    const { places } = await import('./records');
    renderHook(() => places.useList({ campaign_id: 'w1' }));
    await waitFor(() => expect(list).toHaveBeenCalled());
    const [path, key, , params] = list.mock.calls[0] as [string, string, unknown, Record<string, string>];
    expect([path, key, params]).toEqual(['/v1/location', 'locations', { campaign_id: 'w1' }]);
  });
});
