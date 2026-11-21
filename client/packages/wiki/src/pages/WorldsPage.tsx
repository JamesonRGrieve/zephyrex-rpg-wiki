// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * /w: the settings (operator, 2026-11-21: "settings and campaigns"). Each setting opens its canon
 * (its places, people, organisations, items and lore, the same pages a campaign has) and lists its
 * campaigns, a new one made in it by name; campaigns in no setting come last. Shown when the back
 * end serves campaigns (rpg_core).
 */
import Link from 'next/link';
import type { ReactElement } from 'react';
import { useWrites } from 'zephyrex/hooks/useWrites';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { PageHeader } from 'zephyrex/ui/page-header';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { useWikiBase } from '../base';
import { Unavailable } from '../components/world/Unavailable';
import { WorldList } from '../components/world/WorldList';
import { useCapabilities } from '../features/capabilities';
import { type Setting, settings, type World, worlds } from '../features/data/records';
import { kindPath } from '../lib/paths';
import { settingScope } from '../lib/scope';

function SettingSection({
  setting,
  campaigns,
  writes,
  onCreate,
  onDelete,
}: {
  setting: Setting | null;
  campaigns: readonly World[];
  writes: { problem: string | null };
  onCreate: (name: string) => Promise<boolean>;
  onDelete: (campaign: World) => void;
}): ReactElement {
  const base = useWikiBase();
  const title = setting?.name ?? 'In no setting';
  const id = `setting-${setting?.id ?? 'none'}`;
  return (
    <section aria-labelledby={id} className='grid gap-3'>
      <div className='flex flex-wrap items-baseline justify-between gap-2'>
        <h2 id={id} className='text-xl font-semibold'>
          {title}
        </h2>
        {setting !== null && (
          <Link href={kindPath(base, settingScope(setting.id), 'location')} className='text-sm underline-offset-4 hover:underline'>
            Its canon: places, people and lore
          </Link>
        )}
      </div>
      <WorldList
        worlds={campaigns}
        onCreate={onCreate}
        onDelete={onDelete}
        problem={writes.problem}
        newLabel={`New campaign in ${title}`}
        listLabel={`Campaigns in ${title}`}
        quietEmpty
      />
    </section>
  );
}

function Settings(): ReactElement {
  const all = settings.useList();
  const campaigns = worlds.useList();
  const { create, remove } = worlds.useActions();
  const writes = useWrites(() => campaigns.mutate());
  if (all.error !== undefined || campaigns.error !== undefined)
    return (
      <LoadProblem
        what='the settings'
        error={(all.error ?? campaigns.error) as Error}
        onRetry={() => Promise.all([all.mutate(), campaigns.mutate()])}
      />
    );
  if (all.data === undefined || campaigns.data === undefined) return <SkeletonRows rows={3} label='Loading the settings' />;
  const held = campaigns.data;
  const known = new Set(all.data.map((setting) => setting.id));
  const loose = held.filter((campaign) => !campaign.setting_id || !known.has(campaign.setting_id));
  const sections: { setting: Setting | null; campaigns: World[] }[] = [
    ...all.data.map((setting) => ({ setting, campaigns: held.filter((campaign) => campaign.setting_id === setting.id) })),
    ...(loose.length > 0 ? [{ setting: null, campaigns: loose }] : []),
  ];
  return (
    <div className='grid gap-10'>
      {sections.map(({ setting, campaigns: inSetting }) => (
        <SettingSection
          key={setting?.id ?? 'none'}
          setting={setting}
          campaigns={inSetting}
          writes={writes}
          onCreate={(name) =>
            writes.run(create({ name, ...(setting === null ? {} : { setting_id: setting.id }) }), 'The campaign could not be made', `${name} made`)
          }
          onDelete={(campaign) => void writes.run(remove(campaign), 'The campaign could not be deleted')}
        />
      ))}
    </div>
  );
}

export function WorldsPage(): ReactElement {
  const can = useCapabilities();
  return (
    <main className='mx-auto grid w-full max-w-3xl content-start gap-6 px-4 py-8'>
      <PageHeader title='Settings' description='Each setting keeps its canon, and its campaigns their own places and people.' />
      {!can.loaded ? <SkeletonRows rows={2} label='Loading' /> : can.worlds ? <Settings /> : <Unavailable what='settings' />}
    </main>
  );
}
