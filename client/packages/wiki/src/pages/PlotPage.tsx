// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/plot: a world's plot board (W57): its hooks by where they stand. */
import Link from 'next/link';

import type { ReactElement } from 'react';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { PlotBoard } from '../components/world/PlotBoard';
import { Unavailable } from '../components/world/Unavailable';
import { useCapabilities } from '../features/capabilities';
import { usePlot } from '../features/data/plot';
import { worlds } from '../features/data/records';
import { useWikiBase } from '../base';

function Board({ world }: { world: string }): ReactElement {
  const base = useWikiBase();
  const plot = usePlot(world);
  const rows = plot.hooks?.map((hook) => ({ id: hook.id, name: hook.name, href: `${base}/${world}/hook/${hook.id}`, state: plot.stateOf(hook), excuse: hook.excuse }));
  return <PlotBoard hooks={rows} error={plot.error} onRetry={plot.retry} />;
}

export function PlotPage(params: { world: string }): ReactElement {
  const base = useWikiBase();
  const can = useCapabilities();
  const world = worlds.useOne(params.world);
  return (
    <main className='mx-auto grid w-full max-w-5xl content-start gap-6 px-4 py-8'>
      <PageHeader title={world.data === undefined ? 'Plot board' : `Plot board of ${world.data.name}`} />
      <Link href={`${base}/${params.world}/hook`} className='text-sm underline-offset-4 hover:underline'>
        All hooks
      </Link>
      {!can.loaded ? <SkeletonRows rows={3} label='Loading' /> : can.hooks ? <Board world={params.world} /> : <Unavailable what='hooks' />}
    </main>
  );
}
