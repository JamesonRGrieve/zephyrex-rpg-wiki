// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** A record's picture by link, read and written through its own resource (any that carries one). */
import type { ReactElement } from 'react';
import type { SWRResponse } from 'swr';
import { useWrites } from 'zephyrex/hooks/useWrites';
import { PicturePanel } from './PicturePanel';

interface WithPicture {
  id: string;
  name: string;
  picture_url?: string | null;
}

/** What PictureOf needs of a resource: every record one in features/data/records fits. */
interface PictureResource<T extends WithPicture> {
  useOne(id: string | null): SWRResponse<T, Error>;
  useActions(): { update(seen: T, changes: { picture_url: string }): Promise<T> };
}

export function PictureOf<T extends WithPicture>({ resource, id }: { resource: PictureResource<T>; id: string }): ReactElement | null {
  const one = resource.useOne(id);
  const { update } = resource.useActions();
  const writes = useWrites(() => one.mutate());
  const record = one.data;
  if (record === undefined) return null;
  return (
    <PicturePanel
      name={record.name}
      url={record.picture_url}
      onSave={async (next) =>
        // "" takes it off (as both back ends read it).
        (await writes.run(update(record, { picture_url: next ?? '' }), 'The picture could not be saved', 'Picture saved')) ? null : 'The picture could not be saved'
      }
    />
  );
}
