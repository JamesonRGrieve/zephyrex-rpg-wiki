// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * /w/last/[kind]: the sidebar's Places, People, Organisations, Items, Lore, Plot and Game systems.
 * Opens that page of the setting or campaign the person was last in, or Settings when there is none
 * (a setting has no plot board: its campaigns do).
 */
import { useRouter } from 'next/navigation';
import { type ReactElement, useEffect } from 'react';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { useWikiBase } from '../base';
import { isEntityKind } from '../components/world/kinds';
import { lastScope } from '../lib/lastScope';
import { kindPath, plotPath } from '../lib/paths';
import { settingOf } from '../lib/scope';

/** Where the sidebar's entry leads from a scope: a kind's list, the plot board, or a setting's sections. */
export function lastScopePath(base: string, scope: string | null, kind: string): string {
  if (scope === null) return base;
  if (kind === 'plot') return settingOf(scope) === null ? plotPath(base, scope) : base;
  if (kind === 'systems') {
    // The game-systems section's heading, as SettingSectionsOf names it: "<section id>-<setting id>".
    const setting = settingOf(scope);
    return setting === null ? base : `${kindPath(base, scope, 'location')}#game-systems-${setting}`;
  }
  return isEntityKind(kind) ? kindPath(base, scope, kind) : base;
}

export function LastScopePage({ kind }: { kind: string }): ReactElement {
  const base = useWikiBase();
  const router = useRouter();
  useEffect(() => {
    router.replace(lastScopePath(base, lastScope(), kind));
  }, [base, kind, router]);
  return (
    <main className='mx-auto grid w-full max-w-5xl content-start gap-6 px-4 py-8'>
      <SkeletonRows rows={2} label='Opening' />
    </main>
  );
}
