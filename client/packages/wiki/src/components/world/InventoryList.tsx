// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * What an entity carries now (W8): each item, linked to its page, with how many. Read-only on the
 * entity's page; carrying is changed where the item is. Four states, as every data view.
 */
import Link from 'next/link';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';

export interface CarriedLine {
  id: string;
  /** The item's name, or null while it loads (or if it's gone). */
  name: string | null;
  href: string | null;
  quantity: number;
}

export function InventoryList({
  lines,
  error,
  onRetry,
}: {
  lines: readonly CarriedLine[] | undefined;
  error?: Error;
  onRetry?: () => Promise<unknown>;
}): ReactElement {
  return (
    <section aria-labelledby='carries-title' className='space-y-3'>
      <h2 id='carries-title' className='text-lg font-semibold'>
        Carries
      </h2>
      {error !== undefined && <LoadProblem what='what this carries' error={error} onRetry={onRetry} />}
      {lines === undefined && error === undefined && <SkeletonRows rows={2} label='Loading what this carries' />}
      {lines !== undefined && lines.length === 0 && <p className='text-sm text-muted-foreground'>Nothing carried.</p>}
      {lines !== undefined && lines.length > 0 && (
        <ul aria-label='Carried items' className='divide-y rounded-xl border'>
          {lines.map((line) => (
            <li key={line.id} className='flex min-h-12 items-center justify-between gap-3 px-3'>
              {line.href === null || line.name === null ? (
                <span className='text-muted-foreground'>{line.name ?? 'An item'}</span>
              ) : (
                <Link href={line.href} className='underline underline-offset-4'>
                  {line.name}
                </Link>
              )}
              <span className='tabular-nums text-muted-foreground'>{`× ${line.quantity}`}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
