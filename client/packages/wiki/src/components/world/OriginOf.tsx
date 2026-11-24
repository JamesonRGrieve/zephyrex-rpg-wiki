// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** A campaign's or record's origin, read and written through its own resource (any that carries one). */
import type { ReactElement } from 'react';
import type { SWRResponse } from 'swr';
import { useWrites } from 'zephyrex/hooks/useWrites';
import { ProvenancePanel } from './ProvenancePanel';

interface WithOrigin {
  id: string;
  provenance?: string | null;
  source?: string | null;
}

/** What OriginOf needs of a resource: every one in features/data/records fits. */
interface OriginResource<T extends WithOrigin> {
  useOne(id: string | null): SWRResponse<T, Error>;
  useActions(): { update(seen: T, changes: { provenance: string; source: string }): Promise<T> };
}

export function OriginOf<T extends WithOrigin>({ resource, id, readOnly = false }: { resource: OriginResource<T>; id: string; readOnly?: boolean }): ReactElement | null {
  const one = resource.useOne(id);
  const { update } = resource.useActions();
  const writes = useWrites(() => one.mutate());
  const record = one.data;
  if (record === undefined) return null;
  return (
    <ProvenancePanel
      provenance={record.provenance}
      source={record.source}
      // Read only for a player (the page's viewer, features/viewer).
      onSave={readOnly ? undefined : async (next) =>
        // "" clears a source (as both back ends read it).
        (await writes.run(update(record, { provenance: next.provenance, source: next.source ?? '' }), 'The origin could not be saved', 'Origin saved'))
          ? null
          : 'The origin could not be saved'
      }
    />
  );
}
