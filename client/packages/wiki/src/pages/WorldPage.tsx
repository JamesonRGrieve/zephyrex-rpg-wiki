// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/about: a world (a campaign, or a scenario in rpg-ai) itself: its description and where it came from. */
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { OriginOf } from '../components/world/OriginOf';
import { Unavailable } from '../components/world/Unavailable';
import { WorldNav } from '../components/world/WorldNav';
import { useCapabilities } from '../features/capabilities';
import { worlds } from '../features/data/records';

function About({ world }: { world: string }): ReactElement {
  const one = worlds.useOne(world);
  if (one.error !== undefined) return <LoadProblem what='this world' error={one.error} onRetry={() => one.mutate()} />;
  if (one.data === undefined) return <SkeletonRows rows={2} label='Loading' />;
  return (
    <section aria-label='About this world' className='grid gap-4'>
      {one.data.description !== null && one.data.description !== '' && <p className='whitespace-pre-line'>{one.data.description}</p>}
      <OriginOf resource={worlds} id={world} />
    </section>
  );
}

export function WorldPage(params: { world: string }): ReactElement {
  const can = useCapabilities();
  const world = worlds.useOne(params.world);
  return (
    <main className='mx-auto grid w-full max-w-5xl content-start gap-6 px-4 py-8'>
      <PageHeader title={world.data?.name ?? 'Loading'} />
      <WorldNav world={params.world} current='about' />
      {!can.loaded ? <SkeletonRows rows={2} label='Loading' /> : can.worlds ? <About world={params.world} /> : <Unavailable what='worlds' />}
    </main>
  );
}
