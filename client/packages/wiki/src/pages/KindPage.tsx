// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/[kind]: one world's places, people, organisations, items, journals or hooks. Trees show beside places and organisations. */
import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { ReactElement } from 'react';
import { useWrites } from 'zephyrex/hooks/useWrites';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { EntityList, type EntityRow } from '../components/world/EntityList';
import { ENTITY_KINDS, type EntityKind, isEntityKind } from '../components/world/kinds';
import { ParentTree, type TreeRow } from '../components/world/ParentTree';
import { Unavailable } from '../components/world/Unavailable';
import { useCapabilities } from '../features/capabilities';
import { factions, hooks, items, journals, people, places, type ResourceHooks } from '../features/data/records';
import { isCanon, scopeFields, scopeQuery, settingOf, settingScope } from '../lib/scope';
import { useScope } from '../features/data/scopes';
import { SettingSectionsOf, useWikiBase } from '../base';
import { WorldNav } from '../components/world/WorldNav';
import { recordPath } from '../lib/paths';

/** The four resources a world lists, each with the hooks the list uses. */
const RESOURCES = { location: places, person: people, faction: factions, item: items, journal: journals, hook: hooks } as const;
/** The shape every kind's list reads (each resource has it; the casts below name it). */
type ListedRow = EntityRow & TreeRow & { created_at: string; updated_at: string | null; campaign_id?: string | null };

const TREE_LABELS: Partial<Record<EntityKind, string>> = {
  location: 'Places by where they sit',
  faction: 'Organisations by who they answer to',
};

function KindList({ world, kind }: { world: string; kind: EntityKind }): ReactElement {
  const base = useWikiBase();
  // Every resource here has the same shape the list reads; the cast names that shared shape.
  const resource = RESOURCES[kind] as unknown as ResourceHooks<
    ListedRow,
    { name: string; kind: string | null; campaign_id?: string | null; setting_id?: string },
    object
  >;
  const words = ENTITY_KINDS[kind];
  const list = resource.useList(scopeQuery(world));
  // A setting's own page lists its canon: its records with no campaign.
  const rows = settingOf(world) === null ? list.data : list.data?.filter(isCanon);
  const { create, remove } = resource.useActions();
  const writes = useWrites(() => list.mutate());
  const hrefOf = (row: { id: string }) => recordPath(base, world, kind, row.id);
  const label = TREE_LABELS[kind];
  const facts = rows?.filter((row) => row.is_template !== true);
  return (
    <EntityList
      {...words}
      rows={rows}
      error={list.error}
      onRetry={() => list.mutate()}
      hrefOf={hrefOf}
      onCreate={(fields) =>
        writes.run(create({ ...fields, ...scopeFields(world) }), `The ${words.what} could not be added`, `${fields.name} added`)
      }
      onDelete={(row) => void writes.run(remove(row), `The ${words.what} could not be deleted`)}
      problem={writes.problem}
      aside={
        // The scope's own tree: a template (S4b) is copied into campaigns, never one of its places.
        label !== undefined && facts !== undefined && facts.length > 0 ? <ParentTree rows={facts} label={label} hrefOf={hrefOf} /> : undefined
      }
    />
  );
}

/** A campaign's view of its setting's canon of a kind: read only here, opened on the setting's pages. */
function CanonList({ setting, kind }: { setting: string; kind: EntityKind }): ReactElement | null {
  const base = useWikiBase();
  const resource = RESOURCES[kind] as unknown as ResourceHooks<ListedRow, object, object>;
  const list = resource.useList({ setting_id: setting });
  const canon = list.data?.filter((row) => isCanon(row) && row.is_template !== true) ?? [];
  if (canon.length === 0) return null;
  const words = ENTITY_KINDS[kind];
  return (
    <section aria-labelledby={`canon-${kind}`} className='grid gap-2'>
      <h2 id={`canon-${kind}`} className='text-lg font-semibold'>{`${words.title} of the setting`}</h2>
      <ul className='divide-y rounded-xl border'>
        {canon.map((row) => (
          <li key={row.id} className='flex min-h-12 items-center gap-3 px-4 py-2'>
            <Link href={recordPath(base, settingScope(setting), kind, row.id)} className='min-w-0 flex-1 truncate font-medium underline-offset-4 hover:underline'>
              {row.name}
            </Link>
            <span className='shrink-0 rounded-full border px-2 py-0.5 text-xs'>Canon</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function KindPage(params: { world: string; kind: string }): ReactElement {
  const can = useCapabilities();
  const scope = useScope(params.world);
  if (!isEntityKind(params.kind)) notFound();
  const kind: EntityKind = params.kind;
  const words = ENTITY_KINDS[kind];
  return (
    <main className='mx-auto grid w-full max-w-5xl content-start gap-6 px-4 py-8'>
      <PageHeader title={scope.name === undefined ? words.title : `${words.title} of ${scope.name}`} />
      <WorldNav world={params.world} current={kind} />
      {!can.loaded ? (
        <SkeletonRows rows={3} label='Loading' />
      ) : can[words.needs] ? (
        <>
          <KindList key={kind} world={params.world} kind={kind} />
          {!scope.isSetting && scope.settingId && <CanonList setting={scope.settingId} kind={kind} />}
          {scope.isSetting && scope.settingId && <SettingSectionsOf settingId={scope.settingId} />}
        </>
      ) : (
        <Unavailable what={words.plural} />
      )}
    </main>
  );
}
