// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A world's plot board (W57, dh-campaign's tracker dashboard): its hooks grouped by where they stand,
 * what can happen now first, then what needs a check at the table, what's blocked (with the GM's
 * excuse) and what has happened. Four states, as every data view.
 */
import Link from 'next/link';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import type { HookState } from '../../lib/requirements';

export interface BoardHook {
  id: string;
  name: string;
  href: string;
  state: HookState;
  excuse: string | null;
}

const COLUMNS: { state: HookState; title: string; empty: string }[] = [
  { state: 'available', title: 'Can happen now', empty: 'Nothing is ready.' },
  { state: 'needs_check', title: 'Needs a check at the table', empty: 'No checks waiting.' },
  { state: 'blocked', title: 'Blocked', empty: 'Nothing is blocked.' },
  { state: 'resolved', title: 'Happened', empty: 'Nothing has happened yet.' },
];

export function PlotBoard({ hooks, error, onRetry }: { hooks: readonly BoardHook[] | undefined; error?: Error; onRetry?: () => Promise<unknown> }): ReactElement {
  if (error !== undefined) return <LoadProblem what='the plot board' error={error} onRetry={onRetry} />;
  if (hooks === undefined) return <SkeletonRows rows={4} label='Loading the plot board' />;
  if (hooks.length === 0)
    return <p className='rounded-xl border border-dashed p-8 text-center text-muted-foreground'>No hooks in this campaign yet. Add one from Hooks.</p>;
  return (
    <div className='grid gap-6 md:grid-cols-2'>
      {COLUMNS.map(({ state, title, empty }) => {
        const rows = hooks.filter((hook) => hook.state === state);
        return (
          <section key={state} aria-labelledby={`plot-${state}`} className='space-y-2'>
            <h2 id={`plot-${state}`} className='text-lg font-semibold'>
              {title} <span className='text-sm font-normal text-muted-foreground'>{rows.length}</span>
            </h2>
            {rows.length === 0 ? (
              <p className='text-sm text-muted-foreground'>{empty}</p>
            ) : (
              <ul aria-label={title} className='divide-y rounded-xl border'>
                {rows.map((hook) => (
                  <li key={hook.id} className='px-3 py-2'>
                    <Link href={hook.href} className='inline-flex min-h-11 items-center underline underline-offset-4'>
                      {hook.name}
                    </Link>
                    {state === 'blocked' && hook.excuse !== null && <p className='text-sm text-muted-foreground'>{hook.excuse}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
