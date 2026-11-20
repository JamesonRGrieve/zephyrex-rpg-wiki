// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * /w/[world]/[kind]/[id]: one place's or person's page. DESIGN's Screens table wrote `/e/[id]`; with
 * a table per kind (OBJECT_PLAN), the kind is in the path so the page knows which to read.
 */
import Link from 'next/link';
import { notFound, useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { EntityPage } from '~/components/world/EntityPage';
import { ENTITY_KINDS, isEntityKind } from '~/components/world/kinds';
import { Unavailable } from '~/components/world/Unavailable';
import { useCapabilities } from '~/features/capabilities';
import { type Person, type Place, people, places } from '~/features/data/records';

function Record({ record, error, onRetry, where, back }: {
  record: Place | Person | undefined;
  error: Error | undefined;
  onRetry: () => Promise<unknown>;
  where: { label: string; name: string; href: string } | undefined;
  back: { href: string; label: string };
}): ReactElement {
  return (
    <>
      <PageHeader title={record?.name ?? 'Loading'} />
      <Link href={back.href} className='text-sm underline-offset-4 hover:underline'>
        {back.label}
      </Link>
      {error !== undefined && <LoadProblem what='this page' error={error} onRetry={onRetry} />}
      {record === undefined && error === undefined && <SkeletonRows rows={4} label='Loading' />}
      {record !== undefined && <EntityPage kind={record.kind} entry={record.entry} description={record.description} where={where} />}
    </>
  );
}

function PlacePage({ world, id }: { world: string; id: string }): ReactElement {
  const one = places.useOne(id);
  const parent = places.useOne(one.data?.parent_id ?? null);
  return (
    <Record
      record={one.data}
      error={one.error}
      onRetry={() => one.mutate()}
      where={parent.data === undefined ? undefined : { label: 'In', name: parent.data.name, href: `/w/${world}/location/${parent.data.id}` }}
      back={{ href: `/w/${world}/location`, label: 'All places' }}
    />
  );
}

function PersonPage({ world, id }: { world: string; id: string }): ReactElement {
  const one = people.useOne(id);
  const place = places.useOne(one.data?.location_id ?? null);
  return (
    <Record
      record={one.data}
      error={one.error}
      onRetry={() => one.mutate()}
      where={place.data === undefined ? undefined : { label: 'At', name: place.data.name, href: `/w/${world}/location/${place.data.id}` }}
      back={{ href: `/w/${world}/person`, label: 'All people' }}
    />
  );
}

export default function EntityRecordPage(): ReactElement {
  const params = useParams<{ world: string; kind: string; id: string }>();
  const can = useCapabilities();
  if (!isEntityKind(params.kind)) notFound();
  const words = ENTITY_KINDS[params.kind];
  return (
    <main className='mx-auto grid w-full max-w-3xl gap-6 px-4 py-8'>
      {!can.loaded ? (
        <SkeletonRows rows={3} label='Loading' />
      ) : !can[words.needs] ? (
        <Unavailable what={words.plural} />
      ) : params.kind === 'location' ? (
        <PlacePage world={params.world} id={params.id} />
      ) : (
        <PersonPage world={params.world} id={params.id} />
      )}
    </main>
  );
}
