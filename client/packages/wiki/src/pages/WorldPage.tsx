// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/about: a world (a campaign, or a scenario in rpg-ai) itself: its description and where it came from. */
import { useRouter } from 'next/navigation';
import type { ReactElement } from 'react';
import { useWrites } from 'zephyrex/hooks/useWrites';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { OriginOf } from '../components/world/OriginOf';
import { Unavailable } from '../components/world/Unavailable';
import { WorldNav } from '../components/world/WorldNav';
import { useCapabilities } from '../features/capabilities';
import { entityTaxa, taxa, worlds } from '../features/data/records';
import { useStartScenario } from '../features/data/scenarios';
import { ScenarioPanel } from '../components/world/ScenarioPanel';
import { useWikiBase } from '../base';
import { aboutPath } from '../lib/paths';
import { PlayStyles } from '../components/world/PlayStyles';
import { PLAY_STYLE } from '../contract';

/** The world's play styles (taxons of kind play_style on the campaign), shared ones and one's own. */
function WorldPlayStyles({ world }: { world: string }): ReactElement {
  const links = entityTaxa.useList({ target_entity_type: 'campaign', target_entity_id: world });
  const options = taxa.useList({ kind: PLAY_STYLE });
  const linkActions = entityTaxa.useActions();
  const taxonActions = taxa.useActions();
  const writes = useWrites(async () => {
    await Promise.all([links.mutate(), options.mutate()]);
  });
  const nameOf = new Map((options.data ?? []).map((taxon) => [taxon.id, taxon.name]));
  const styles = (links.data ?? []).flatMap((link) => {
    const name = nameOf.get(link.taxon_id);
    return name === undefined ? [] : [{ id: link.id, name }];
  });
  const attach = (taxonId: string) => linkActions.create({ taxon_id: taxonId, target_entity_type: 'campaign', target_entity_id: world });
  if (links.error !== undefined || options.error !== undefined)
    return <LoadProblem what='its play styles' error={(links.error ?? options.error) as Error} onRetry={() => Promise.all([links.mutate(), options.mutate()])} />;
  return (
    <PlayStyles
      styles={styles}
      options={(options.data ?? []).map((taxon) => ({ id: taxon.id, name: taxon.name }))}
      problem={writes.problem}
      onAdd={(taxonId) => void writes.run(attach(taxonId), 'The play style could not be added')}
      onCreate={(name) =>
        void writes.run(
          taxonActions.create({ name, kind: PLAY_STYLE }).then((made) => attach(made.id)),
          'The play style could not be made',
        )
      }
      onRemove={(style) => {
        const link = links.data?.find((one) => one.id === style.id);
        if (link !== undefined) void writes.run(linkActions.remove(link), 'The play style could not be taken off');
      }}
    />
  );
}

/** A scenario's start, or a playthrough's link back to its scenario. */
function Scenario({ world }: { world: string }): ReactElement | null {
  const base = useWikiBase();
  const router = useRouter();
  const one = worlds.useOne(world);
  const source = worlds.useOne(one.data?.scenario_id ?? null);
  const start = useStartScenario();
  if (one.data === undefined) return null;
  return (
    <ScenarioPanel
      isScenario={one.data.is_scenario === true}
      scenario={source.data === undefined ? null : { name: source.data.name, href: aboutPath(base, source.data.id) }}
      onStart={async (name) => {
        try {
          const made = await start(world, name ?? undefined);
          router.push(aboutPath(base, made.campaign.id));
          return null;
        } catch (error) {
          return `The playthrough could not be started: ${error instanceof Error ? error.message : String(error)}`;
        }
      }}
    />
  );
}

function About({ world }: { world: string }): ReactElement {
  const one = worlds.useOne(world);
  if (one.error !== undefined) return <LoadProblem what='this campaign' error={one.error} onRetry={() => one.mutate()} />;
  if (one.data === undefined) return <SkeletonRows rows={2} label='Loading' />;
  return (
    <section aria-label='About this campaign' className='grid gap-4'>
      {one.data.description !== null && one.data.description !== '' && <p className='whitespace-pre-line'>{one.data.description}</p>}
      <OriginOf resource={worlds} id={world} />
      <Scenario world={world} />
      <WorldPlayStyles world={world} />
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
      {!can.loaded ? <SkeletonRows rows={2} label='Loading' /> : can.worlds ? <About world={params.world} /> : <Unavailable what='campaigns' />}
    </main>
  );
}
