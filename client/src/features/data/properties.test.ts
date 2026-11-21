// SPDX-License-Identifier: AGPL-3.0-or-later
// A record's properties go to the framework's record_metadata paths, the record named in the query
// for reads and in the envelope for writes; a change and a removal carry the row's version.
import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const ROW = {
  id: 'p 1',
  key: 'Population',
  value: '9 billion',
  value_type: 'text',
  ordinal: 0,
  is_private: false,
  created_at: '2026-11-21T00:00:00',
  updated_at: null,
};
const client = {
  url: vi.fn((path: string, params?: Record<string, string>) => `${path}?${new URLSearchParams(params).toString()}`),
  get: vi.fn().mockResolvedValue({ metadata: [ROW] }),
  post: vi.fn().mockResolvedValue({ record_metadata: ROW }),
  patch: vi.fn().mockResolvedValue({ record_metadata: { ...ROW, value: '10 billion' } }),
  delete: vi.fn().mockResolvedValue(null),
};
vi.mock('zephyrex', () => ({ useClient: () => client }));

describe('a record’s properties', () => {
  it('reads them for the record named in the query', async () => {
    const { useProperties } = await import('./properties');
    const view = renderHook(() => ({ rows: useProperties('location', 'l1').data }));
    await waitFor(() => expect(view.result.current.rows).toEqual([ROW]));
    expect(client.get).toHaveBeenCalledWith('/v1/record_metadata/of', { target_entity_type: 'location', target_entity_id: 'l1' });
  });

  it('adds, changes and removes them in the framework’s envelopes, versions included', async () => {
    const { usePropertyActions } = await import('./properties');
    const { result } = renderHook(() => usePropertyActions('location', 'l1'));
    await result.current.add('Garrison', 'number', 1);
    expect(client.post).toHaveBeenCalledWith('/v1/record_metadata', {
      record_metadata: { target_entity_type: 'location', target_entity_id: 'l1', key: 'Garrison', value_type: 'number', ordinal: 1 },
    });
    expect((await result.current.save(ROW, '10 billion')).value).toBe('10 billion');
    expect(client.patch).toHaveBeenCalledWith('/v1/record_metadata/p%201', { record_metadata: { value: '10 billion' } }, ROW);
    await result.current.remove(ROW);
    expect(client.delete).toHaveBeenCalledWith('/v1/record_metadata/p%201', ROW);
  });
});
