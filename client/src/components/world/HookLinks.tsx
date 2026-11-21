// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A hook's place in the plot-hook DAG: what it waits on, what it leads to, and who is on it with
 * their status and progress. Read-only here. Four states, as every data view.
 */
import Link from 'next/link';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';

export interface LinkedHook {
  id: string;
  /** The hook's name, or null while it loads (or if it's gone). */
  name: string | null;
  href: string | null;
}

export interface Taker extends LinkedHook {
  status: string | null;
  progress: number | null;
}

export interface HookLinksProps {
  waitsOn: readonly LinkedHook[] | undefined;
  leadsTo: readonly LinkedHook[] | undefined;
  takers: readonly Taker[] | undefined;
  error?: Error;
  onRetry?: () => Promise<unknown>;
}

function Named({ one, fallback }: { one: LinkedHook; fallback: string }): ReactElement {
  return one.href === null || one.name === null ? (
    <span className='text-muted-foreground'>{one.name ?? fallback}</span>
  ) : (
    <Link href={one.href} className='underline-offset-4 hover:underline'>
      {one.name}
    </Link>
  );
}

function Hooks({ label, rows, empty }: { label: string; rows: readonly LinkedHook[]; empty: string }): ReactElement {
  return (
    <div className='space-y-1'>
      <h3 className='text-sm font-medium'>{label}</h3>
      {rows.length === 0 ? (
        <p className='text-sm text-muted-foreground'>{empty}</p>
      ) : (
        <ul aria-label={label} className='divide-y rounded-xl border'>
          {rows.map((row) => (
            <li key={row.id} className='flex min-h-12 items-center px-3'>
              <Named one={row} fallback='A hook' />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function HookLinks({ waitsOn, leadsTo, takers, error, onRetry }: HookLinksProps): ReactElement {
  const loading = (waitsOn === undefined || leadsTo === undefined || takers === undefined) && error === undefined;
  return (
    <section aria-labelledby='hook-links-title' className='space-y-3'>
      <h2 id='hook-links-title' className='text-lg font-semibold'>
        Plot
      </h2>
      {error !== undefined && <LoadProblem what='this hook’s links' error={error} onRetry={onRetry} />}
      {loading && <SkeletonRows rows={3} label='Loading this hook’s links' />}
      {!loading && error === undefined && waitsOn !== undefined && leadsTo !== undefined && takers !== undefined && (
        <div className='grid gap-4 md:grid-cols-3'>
          <Hooks label='Waits on' rows={waitsOn} empty='Nothing: it can start now.' />
          <Hooks label='Leads to' rows={leadsTo} empty='Nothing waits on it.' />
          <div className='space-y-1'>
            <h3 className='text-sm font-medium'>Who’s on it</h3>
            {takers.length === 0 ? (
              <p className='text-sm text-muted-foreground'>No one yet.</p>
            ) : (
              <ul aria-label='Who’s on it' className='divide-y rounded-xl border'>
                {takers.map((taker) => (
                  <li key={taker.id} className='flex min-h-12 items-center justify-between gap-3 px-3'>
                    <Named one={taker} fallback='Someone' />
                    <span className='text-sm text-muted-foreground'>
                      {[taker.status, taker.progress === null ? null : `${taker.progress}`].filter((part) => part !== null).join(' · ')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
