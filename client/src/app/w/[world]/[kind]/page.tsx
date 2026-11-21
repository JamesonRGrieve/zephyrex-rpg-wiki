// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/[kind]: one world's places, people, organisations, items, journals or hooks. Trees show beside places and organisations. */
import Link from 'next/link';
import { notFound, useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { useWrites } from 'zephyrex/hooks/useWrites';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { EntityList, type EntityRow } from '@zephyrex-rpg/wiki/components/world/EntityList';
import { ENTITY_KINDS, type EntityKind, isEntityKind } from '@zephyrex-rpg/wiki/components/world/kinds';
import { ParentTree, type TreeRow } from '@zephyrex-rpg/wiki/components/world/ParentTree';
import { Unavailable } from '@zephyrex-rpg/wiki/components/world/Unavailable';
import { useCapabilities } from '@zephyrex-rpg/wiki/features/capabilities';
import { factions, hooks, items, journals, people, places, type ResourceHooks, worlds } from '@zephyrex-rpg/wiki/features/data/records';

/** The four resources a world lists, each with the hooks the list uses. */
const RESOURCES = { location: places, person: people, faction: factions, item: items, journal: journals, hook: hooks } as const;
const TREE_LABELS: Partial<Record<EntityKind, string>> = {
  location: 'Places by where they sit',
  faction: 'Organisations by who they answer to',
};

function KindList({ world, kind }: { world: string; kind: EntityKind }): ReactElement {
  // Every resource here has the same shape the list reads; the cast names that shared shape.
  const resource = RESOURCES[kind] as unknown as ResourceHooks<
    EntityRow & TreeRow & { created_at: string; updated_at: string | null },
    { name: string; kind: string | null; campaign_id: string },
    object
  >;
  const words = ENTITY_KINDS[kind];
  const list = resource.useList({ campaign_id: world });
  const { create, remove } = resource.useActions();
  const writes = useWrites(() => list.mutate());
  const hrefOf = (row: { id: string }) => `/w/${world}/${kind}/${row.id}`;
  const label = TREE_LABELS[kind];
  const facts = list.data?.filter((row) => row.is_template !== true);
  return (
    <EntityList
      {...words}
      rows={list.data}
      error={list.error}
      onRetry={() => list.mutate()}
      hrefOf={hrefOf}
      onCreate={(fields) =>
        writes.run(create({ ...fields, campaign_id: world }), `The ${words.what} could not be added`, `${fields.name} added`)
      }
      onDelete={(row) => void writes.run(remove(row), `The ${words.what} could not be deleted`)}
      problem={writes.problem}
      aside={
        // The world's own tree: a template (S4b) is copied into worlds, never one of its places.
        label !== undefined && facts !== undefined && facts.length > 0 ? <ParentTree rows={facts} label={label} hrefOf={hrefOf} /> : undefined
      }
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
    <main className='mx-auto grid w-full max-w-5xl content-start gap-6 px-4 py-8'>
      <PageHeader title={world.data === undefined ? words.title : `${words.title} of ${world.data.name}`} />
      <nav aria-label='This world' className='flex flex-wrap gap-x-4 gap-y-2 text-sm'>
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
        {can.taxonomy && (
          <Link href={`/w/${params.world}/taxonomy`} className='underline-offset-4 hover:underline'>
            Taxonomy
          </Link>
        )}
        {can.hooks && (
          <Link href={`/w/${params.world}/plot`} className='underline-offset-4 hover:underline'>
            Plot board
          </Link>
        )}
      </nav>
      {!can.loaded ? (
        <SkeletonRows rows={3} label='Loading' />
      ) : can[words.needs] ? (
        <KindList key={kind} world={params.world} kind={kind} />
      ) : (
        <Unavailable what={words.plural} />
      )}
    </main>
  );
}
