// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * /w/[world]/taxonomy: a world's tags, categories, races and other classifications as a tree, its
 * statuses, and (with ?taxon=) the records a taxon is on (W6).
 */
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { ENTITY_KINDS, isEntityKind } from '~/components/world/kinds';
import { ParentTree } from '~/components/world/ParentTree';
import { Unavailable } from '~/components/world/Unavailable';
import { useCapabilities } from '~/features/capabilities';
import { entityTaxa, factions, hooks, items, journals, people, places, statuses, taxa, worlds } from '~/features/data/records';

/** The records a taxon is on, each named from its world's lists and linked to its page. */
function Tagged({ world, taxonId }: { world: string; taxonId: string }): ReactElement {
  const links = entityTaxa.useList({ taxon_id: taxonId });
  // One call per kind, always in this order (hooks never run in a loop).
  const scope = { campaign_id: world };
  const lists = [
    places.useList(scope),
    people.useList(scope),
    factions.useList(scope),
    items.useList(scope),
    journals.useList(scope),
    hooks.useList(scope),
  ];
  const nameOf = new Map(lists.flatMap((list) => (list.data ?? []).map((row) => [row.id, row.name] as const)));
  if (links.error !== undefined) return <LoadProblem what='the tagged records' error={links.error} onRetry={() => links.mutate()} />;
  if (links.data === undefined) return <SkeletonRows rows={2} label='Loading the tagged records' />;
  if (links.data.length === 0) return <p className='text-sm text-muted-foreground'>Nothing has this yet.</p>;
  return (
    <ul aria-label='Tagged records' className='divide-y rounded-xl border'>
      {links.data.map((link) => (
        <li key={link.id} className='flex min-h-12 items-center justify-between gap-3 px-3'>
          <Link href={`/w/${world}/${link.target_entity_type}/${link.target_entity_id}`} className='underline underline-offset-4'>
            {nameOf.get(link.target_entity_id) ?? 'A record'}
          </Link>
          <span className='text-sm text-muted-foreground'>
            {isEntityKind(link.target_entity_type) ? ENTITY_KINDS[link.target_entity_type].what : link.target_entity_type}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Taxonomy({ world }: { world: string }): ReactElement {
  const chosen = useSearchParams().get('taxon');
  const all = taxa.useList({ campaign_id: world });
  const states = statuses.useList({ campaign_id: world });
  const picked = chosen === null ? undefined : all.data?.find((row) => row.id === chosen);
  return (
    <div className='grid gap-6 md:grid-cols-2'>
      <section aria-labelledby='taxa-title' className='space-y-3'>
        <h2 id='taxa-title' className='text-lg font-semibold'>
          Tags and classifications
        </h2>
        {all.error !== undefined && <LoadProblem what='the taxonomy' error={all.error} onRetry={() => all.mutate()} />}
        {all.data === undefined && all.error === undefined && <SkeletonRows rows={3} label='Loading the taxonomy' />}
        {all.data !== undefined && all.data.length === 0 && <p className='text-sm text-muted-foreground'>No tags yet.</p>}
        {all.data !== undefined && all.data.length > 0 && (
          <ParentTree rows={all.data} hrefOf={(row) => `/w/${world}/taxonomy?taxon=${row.id}`} label='Tags by where they sit' />
        )}
      </section>
      <div className='space-y-6'>
        {chosen !== null && (
          <section aria-labelledby='tagged-title' className='space-y-3'>
            <h2 id='tagged-title' className='text-lg font-semibold'>
              {picked === undefined ? 'Tagged records' : `With ${picked.name}`}
            </h2>
            <Tagged world={world} taxonId={chosen} />
          </section>
        )}
        <section aria-labelledby='statuses-title' className='space-y-3'>
          <h2 id='statuses-title' className='text-lg font-semibold'>
            Statuses
          </h2>
          {states.error !== undefined && <LoadProblem what='the statuses' error={states.error} onRetry={() => states.mutate()} />}
          {states.data === undefined && states.error === undefined && <SkeletonRows rows={2} label='Loading the statuses' />}
          {states.data !== undefined && states.data.length === 0 && <p className='text-sm text-muted-foreground'>No statuses yet.</p>}
          {states.data !== undefined && states.data.length > 0 && (
            <ul aria-label='Statuses' className='flex flex-wrap gap-2'>
              {states.data.map((row) => (
                <li key={row.id} className='inline-flex min-h-11 items-center gap-1.5 rounded-full border px-3 text-sm'>
                  {row.colour !== null && <span aria-hidden className='size-2.5 rounded-full' style={{ backgroundColor: row.colour }} />}
                  {row.name}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

export default function WorldTaxonomyPage(): ReactElement {
  const params = useParams<{ world: string }>();
  const can = useCapabilities();
  const world = worlds.useOne(params.world);
  return (
    <main className='mx-auto grid w-full max-w-5xl content-start gap-6 px-4 py-8'>
      <PageHeader title={world.data === undefined ? 'Taxonomy' : `Taxonomy of ${world.data.name}`} />
      <Link href={`/w/${params.world}/location`} className='text-sm underline-offset-4 hover:underline'>
        Back to the world
      </Link>
      {!can.loaded ? <SkeletonRows rows={3} label='Loading' /> : can.taxonomy ? <Taxonomy world={params.world} /> : <Unavailable what='tags' />}
    </main>
  );
}
