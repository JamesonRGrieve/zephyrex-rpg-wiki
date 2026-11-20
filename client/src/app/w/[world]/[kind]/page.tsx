// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/[kind]: one world's places or people. Places also show as their tree. */
import Link from 'next/link';
import { notFound, useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { useWrites } from 'zephyrex/hooks/useWrites';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { EntityList } from '~/components/world/EntityList';
import { ENTITY_KINDS, type EntityKind, isEntityKind } from '~/components/world/kinds';
import { LocationTree } from '~/components/world/LocationTree';
import { Unavailable } from '~/components/world/Unavailable';
import { useCapabilities } from '~/features/capabilities';
import { people, places, worlds } from '~/features/data/records';

function Places({ world }: { world: string }): ReactElement {
  const list = places.useList({ campaign_id: world });
  const { create, remove } = places.useActions();
  const writes = useWrites(() => list.mutate());
  const hrefOf = (row: { id: string }) => `/w/${world}/location/${row.id}`;
  return (
    <EntityList
      {...ENTITY_KINDS.location}
      rows={list.data}
      error={list.error}
      onRetry={() => list.mutate()}
      hrefOf={hrefOf}
      onCreate={(fields) => writes.run(create({ ...fields, campaign_id: world }), 'The place could not be added', `${fields.name} added`)}
      onDelete={(row) => void writes.run(remove(row), 'The place could not be deleted')}
      problem={writes.problem}
      aside={list.data !== undefined && list.data.length > 0 ? <LocationTree places={list.data} hrefOf={hrefOf} /> : undefined}
    />
  );
}

function People({ world }: { world: string }): ReactElement {
  const list = people.useList({ campaign_id: world });
  const { create, remove } = people.useActions();
  const writes = useWrites(() => list.mutate());
  return (
    <EntityList
      {...ENTITY_KINDS.person}
      rows={list.data}
      error={list.error}
      onRetry={() => list.mutate()}
      hrefOf={(row) => `/w/${world}/person/${row.id}`}
      onCreate={(fields) => writes.run(create({ ...fields, campaign_id: world }), 'The person could not be added', `${fields.name} added`)}
      onDelete={(row) => void writes.run(remove(row), 'The person could not be deleted')}
      problem={writes.problem}
    />
  );
}

export default function WorldKindPage(): ReactElement {
  const params = useParams<{ world: string; kind: string }>();
  const can = useCapabilities();
  const world = worlds.useOne(params.world);
  if (!isEntityKind(params.kind)) notFound();
  const kind: EntityKind = params.kind;
  const words = ENTITY_KINDS[kind];
  return (
    <main className='mx-auto grid w-full max-w-5xl gap-6 px-4 py-8'>
      <PageHeader title={world.data === undefined ? words.title : `${words.title} of ${world.data.name}`} />
      <nav aria-label='This world' className='flex gap-4 text-sm'>
        <Link href='/w' className='underline-offset-4 hover:underline'>
          All worlds
        </Link>
        {Object.entries(ENTITY_KINDS).map(([path, one]) => (
          <Link
            key={path}
            href={`/w/${params.world}/${path}`}
            aria-current={path === kind ? 'page' : undefined}
            className='underline-offset-4 hover:underline aria-[current=page]:font-semibold'
          >
            {one.title}
          </Link>
        ))}
      </nav>
      {!can.loaded ? (
        <SkeletonRows rows={3} label='Loading' />
      ) : !can[words.needs] ? (
        <Unavailable what={words.plural} />
      ) : kind === 'location' ? (
        <Places world={params.world} />
      ) : (
        <People world={params.world} />
      )}
    </main>
  );
}
