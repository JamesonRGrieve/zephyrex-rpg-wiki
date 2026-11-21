// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w: the person's worlds. Shown when the back end serves worlds (rpg_core). */
import type { ReactElement } from 'react';
import { useWrites } from 'zephyrex/hooks/useWrites';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { Unavailable } from '~/components/world/Unavailable';
import { WorldList } from '~/components/world/WorldList';
import { useCapabilities } from '~/features/capabilities';
import { worlds } from '~/features/data/records';

function Worlds(): ReactElement {
  const list = worlds.useList();
  const { create, remove } = worlds.useActions();
  const writes = useWrites(() => list.mutate());
  return (
    <WorldList
      worlds={list.data}
      error={list.error}
      onRetry={() => list.mutate()}
      onCreate={(name) => writes.run(create({ name }), 'The world could not be made', `${name} made`)}
      onDelete={(world) => void writes.run(remove(world), 'The world could not be deleted')}
      problem={writes.problem}
    />
  );
}

export default function WorldsPage(): ReactElement {
  const can = useCapabilities();
  return (
    <main className='mx-auto grid w-full max-w-3xl content-start gap-6 px-4 py-8'>
      <PageHeader title='Your worlds' description='Each world keeps its own places and people.' />
      {!can.loaded ? <SkeletonRows rows={2} label='Loading' /> : can.worlds ? <Worlds /> : <Unavailable what='worlds' />}
    </main>
  );
}
