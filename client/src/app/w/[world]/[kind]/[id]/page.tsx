// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * /w/[world]/[kind]/[id]: one place's, person's, organisation's or item's page: its entry, where it
 * sits, and what it carries (W8). DESIGN's Screens table wrote `/e/[id]`; with a table per kind
 * (OBJECT_PLAN), the kind is in the path so the page knows which to read.
 */
import Link from 'next/link';
import { notFound, useParams } from 'next/navigation';
import type { ReactElement, ReactNode } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { EntityPage, type EntityPageProps } from '~/components/world/EntityPage';
import { HookLinks, type LinkedHook, type Taker } from '~/components/world/HookLinks';
import { type CarriedLine, InventoryList } from '~/components/world/InventoryList';
import { PostList } from '~/components/world/PostList';
import { ENTITY_KINDS, type EntityKind, isEntityKind } from '~/components/world/kinds';
import { Unavailable } from '~/components/world/Unavailable';
import { type Capabilities, useCapabilities } from '~/features/capabilities';
import {
  carried,
  factionHooks,
  factions,
  hookDependencies,
  hooks,
  itemInstances,
  items,
  journals,
  people,
  personHooks,
  places,
  posts,
} from '~/features/data/records';

interface Shown {
  name: string;
  kind: string | null;
  entry: string | null;
  description: string | null;
}

/** What `target` carries, each line named by its item. */
function Carries({ world, type, id }: { world: string; type: EntityKind; id: string }): ReactElement {
  const rows = carried.useList({ target_entity_type: type, target_entity_id: id });
  const instances = itemInstances.useList();
  const catalogue = items.useList({ campaign_id: world });
  const itemOf = new Map((instances.data ?? []).map((one) => [one.id, one.item_id]));
  const nameOf = new Map((catalogue.data ?? []).map((one) => [one.id, one.name]));
  const lines: CarriedLine[] | undefined = rows.data?.map((row) => {
    const itemId = row.item_instance_id === null ? null : (itemOf.get(row.item_instance_id) ?? null);
    const name = itemId === null ? null : (nameOf.get(itemId) ?? null);
    return { id: row.id, name, href: itemId === null ? null : `/w/${world}/item/${itemId}`, quantity: row.quantity ?? 1 };
  });
  return <InventoryList lines={lines} error={rows.error} onRetry={() => rows.mutate()} />;
}

/** The posts on the record (W3), pinned first. */
function Posts({ type, id }: { type: EntityKind; id: string }): ReactElement {
  const rows = posts.useList({ target_entity_type: type, target_entity_id: id });
  return <PostList posts={rows.data} error={rows.error} onRetry={() => rows.mutate()} />;
}

function Record({
  world,
  kind,
  id,
  record,
  error,
  onRetry,
  where,
  canCarry,
  canPost,
  extra,
}: {
  world: string;
  kind: EntityKind;
  id: string;
  record: Shown | undefined;
  error: Error | undefined;
  onRetry: () => Promise<unknown>;
  where: EntityPageProps['where'];
  canCarry: boolean;
  canPost: boolean;
  /** Kind-specific sections, after the entry (a hook's plot links). */
  extra?: ReactNode;
}): ReactElement {
  const words = ENTITY_KINDS[kind];
  return (
    <>
      <PageHeader title={record?.name ?? 'Loading'} />
      <Link href={`/w/${world}/${kind}`} className='text-sm underline-offset-4 hover:underline'>
        {`All ${words.plural}`}
      </Link>
      {error !== undefined && <LoadProblem what='this page' error={error} onRetry={onRetry} />}
      {record === undefined && error === undefined && <SkeletonRows rows={4} label='Loading' />}
      {record !== undefined && (
        <>
          <EntityPage kind={record.kind} entry={record.entry} description={record.description} where={where} />
          {extra}
          {canPost && <Posts type={kind} id={id} />}
          {canCarry && <Carries world={world} type={kind} id={id} />}
        </>
      )}
    </>
  );
}

const placeHref = (world: string, id: string) => `/w/${world}/location/${id}`;

function PlacePage({ world, id, can }: { world: string; id: string; can: Capabilities }): ReactElement {
  const one = places.useOne(id);
  const parent = places.useOne(one.data?.parent_id ?? null);
  const where = parent.data === undefined ? undefined : { label: 'In', name: parent.data.name, href: placeHref(world, parent.data.id) };
  return <Record world={world} kind='location' id={id} record={one.data} error={one.error} onRetry={() => one.mutate()} where={where} canCarry={can.items} canPost={can.posts} />;
}

function PersonPage({ world, id, can }: { world: string; id: string; can: Capabilities }): ReactElement {
  const one = people.useOne(id);
  const place = places.useOne(one.data?.location_id ?? null);
  const where = place.data === undefined ? undefined : { label: 'At', name: place.data.name, href: placeHref(world, place.data.id) };
  return <Record world={world} kind='person' id={id} record={one.data} error={one.error} onRetry={() => one.mutate()} where={where} canCarry={can.items} canPost={can.posts} />;
}

function FactionPage({ world, id, can }: { world: string; id: string; can: Capabilities }): ReactElement {
  const one = factions.useOne(id);
  const parent = factions.useOne(one.data?.parent_id ?? null);
  const where =
    parent.data === undefined ? undefined : { label: 'Part of', name: parent.data.name, href: `/w/${world}/faction/${parent.data.id}` };
  return <Record world={world} kind='faction' id={id} record={one.data} error={one.error} onRetry={() => one.mutate()} where={where} canCarry={can.items} canPost={can.posts} />;
}

function ItemPage({ world, id, can }: { world: string; id: string; can: Capabilities }): ReactElement {
  const one = items.useOne(id);
  return <Record world={world} kind='item' id={id} record={one.data} error={one.error} onRetry={() => one.mutate()} where={undefined} canCarry={can.items} canPost={can.posts} />;
}

function JournalPage({ world, id, can }: { world: string; id: string; can: Capabilities }): ReactElement {
  const one = journals.useOne(id);
  const place = places.useOne(one.data?.location_id ?? null);
  const where = place.data === undefined ? undefined : { label: 'At', name: place.data.name, href: placeHref(world, place.data.id) };
  return (
    <Record world={world} kind='journal' id={id} record={one.data} error={one.error} onRetry={() => one.mutate()} where={where} canCarry={false} canPost={can.posts} />
  );
}

/** A hook's prerequisites, what it leads to, and who is on it, each named and linked. */
function Plot({ world, id }: { world: string; id: string }): ReactElement {
  const waits = hookDependencies.useList({ child_hook_id: id });
  const leads = hookDependencies.useList({ parent_hook_id: id });
  const mine = personHooks.useList({ hook_id: id });
  const theirs = factionHooks.useList({ hook_id: id });
  const allHooks = hooks.useList({ campaign_id: world });
  const allPeople = people.useList({ campaign_id: world });
  const allFactions = factions.useList({ campaign_id: world });
  const nameOf = (rows: readonly { id: string; name: string }[] | undefined) => new Map((rows ?? []).map((row) => [row.id, row.name]));
  const hookName = nameOf(allHooks.data);
  const personName = nameOf(allPeople.data);
  const factionName = nameOf(allFactions.data);
  const linked = (hookId: string): LinkedHook => ({ id: hookId, name: hookName.get(hookId) ?? null, href: `/w/${world}/hook/${hookId}` });
  const takers: Taker[] | undefined =
    mine.data === undefined || theirs.data === undefined
      ? undefined
      : [
          ...mine.data.map((row) => ({
            id: row.id,
            name: personName.get(row.person_id) ?? null,
            href: `/w/${world}/person/${row.person_id}`,
            status: row.status,
            progress: row.progress,
          })),
          ...theirs.data.map((row) => ({
            id: row.id,
            name: factionName.get(row.faction_id) ?? null,
            href: `/w/${world}/faction/${row.faction_id}`,
            status: row.status,
            progress: row.progress,
          })),
        ];
  const error = waits.error ?? leads.error ?? mine.error ?? theirs.error;
  return (
    <HookLinks
      waitsOn={waits.data?.map((edge) => linked(edge.parent_hook_id))}
      leadsTo={leads.data?.map((edge) => linked(edge.child_hook_id))}
      takers={takers}
      error={error}
      onRetry={() => Promise.all([waits.mutate(), leads.mutate(), mine.mutate(), theirs.mutate()])}
    />
  );
}

function HookPage({ world, id, can }: { world: string; id: string; can: Capabilities }): ReactElement {
  const one = hooks.useOne(id);
  const giver = people.useOne(one.data?.giver_person_id ?? null);
  const where = giver.data === undefined ? undefined : { label: 'Given by', name: giver.data.name, href: `/w/${world}/person/${giver.data.id}` };
  return (
    <Record
      world={world}
      kind='hook'
      id={id}
      record={one.data}
      error={one.error}
      onRetry={() => one.mutate()}
      where={where}
      canCarry={false}
      canPost={can.posts}
      extra={<Plot world={world} id={id} />}
    />
  );
}

const PAGES = { location: PlacePage, person: PersonPage, faction: FactionPage, item: ItemPage, journal: JournalPage, hook: HookPage } as const;

export default function EntityRecordPage(): ReactElement {
  const params = useParams<{ world: string; kind: string; id: string }>();
  const can = useCapabilities();
  if (!isEntityKind(params.kind)) notFound();
  const words = ENTITY_KINDS[params.kind];
  const Page = PAGES[params.kind];
  return (
    <main className='mx-auto grid w-full max-w-3xl gap-6 px-4 py-8'>
      {!can.loaded ? (
        <SkeletonRows rows={3} label='Loading' />
      ) : can[words.needs] ? (
        <Page key={params.kind} world={params.world} id={params.id} can={can} />
      ) : (
        <Unavailable what={words.plural} />
      )}
    </main>
  );
}
