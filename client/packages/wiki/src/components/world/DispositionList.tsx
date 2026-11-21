// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * How a person regards others now (W56, from dh-campaign's tracker): one line per target (the party,
 * a person, an organisation) with the current attitude, what changed it (or "baseline"), and the
 * note. Read here. Four states, as every data view.
 */
import Link from 'next/link';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { bandOf } from '../../lib/dispositions';

export interface DispositionLine {
  key: string;
  target: string;
  /** The target's page, or null for the party. */
  href: string | null;
  attitude: string | null;
  /** The hook whose resolution set it, or null for the baseline. */
  because: string | null;
  note: string | null;
}

export function DispositionList({ lines, error, onRetry }: { lines: readonly DispositionLine[] | undefined; error?: Error; onRetry?: () => Promise<unknown> }): ReactElement {
  return (
    <section aria-labelledby='dispositions-title' className='space-y-3'>
      <h2 id='dispositions-title' className='text-lg font-semibold'>
        Dispositions
      </h2>
      {error !== undefined && <LoadProblem what='the dispositions' error={error} onRetry={onRetry} />}
      {lines === undefined && error === undefined && <SkeletonRows rows={2} label='Loading the dispositions' />}
      {lines !== undefined && lines.length === 0 && <p className='text-sm text-muted-foreground'>No dispositions yet.</p>}
      {lines !== undefined && lines.length > 0 && (
        <ul aria-label='Dispositions' className='divide-y rounded-xl border'>
          {lines.map((line) => {
            const band = line.attitude === null ? null : bandOf(line.attitude);
            return (
              <li key={line.key} className='space-y-1 px-3 py-2'>
                <p className='flex flex-wrap items-baseline justify-between gap-2'>
                  {line.href === null ? (
                    <span>{line.target}</span>
                  ) : (
                    <Link href={line.href} className='underline underline-offset-4'>
                      {line.target}
                    </Link>
                  )}
                  <span className='font-medium'>
                    {line.attitude ?? 'Unknown'}
                    {band !== null && band !== line.attitude && <span className='text-sm font-normal text-muted-foreground'> ({band})</span>}
                  </span>
                </p>
                <p className='text-sm text-muted-foreground'>{line.because === null ? 'Baseline' : `Since ${line.because}`}</p>
                {line.note !== null && <p className='text-sm'>{line.note}</p>}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
