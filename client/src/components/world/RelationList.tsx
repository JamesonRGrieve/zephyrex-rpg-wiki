// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A person's or organisation's relations (W5): who or what, the kind of tie, the attitude (genealogy's
 * intensity, -1 to +1, shown as -100 to +100), its colour, and whether a mirror reads it the other
 * way. Read-only here. Four states, as every data view.
 */
import { ArrowLeftRight } from 'lucide-react';
import Link from 'next/link';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';

export interface RelationLine {
  id: string;
  /** The other end's name, or null while it loads (or if it's gone). */
  name: string | null;
  href: string | null;
  kind: string | null;
  intensity: number | null;
  colour: string | null;
  mirrored: boolean;
}

/** Attitude as a signed whole number, -100 to +100. */
export function attitudeOf(intensity: number | null): string | null {
  if (intensity === null) return null;
  const value = Math.round(intensity * 100);
  return value > 0 ? `+${value}` : `${value}`;
}

export function RelationList({
  lines,
  error,
  onRetry,
}: {
  lines: readonly RelationLine[] | undefined;
  error?: Error;
  onRetry?: () => Promise<unknown>;
}): ReactElement {
  return (
    <section aria-labelledby='relations-title' className='space-y-3'>
      <h2 id='relations-title' className='text-lg font-semibold'>
        Relations
      </h2>
      {error !== undefined && <LoadProblem what='the relations' error={error} onRetry={onRetry} />}
      {lines === undefined && error === undefined && <SkeletonRows rows={2} label='Loading the relations' />}
      {lines !== undefined && lines.length === 0 && <p className='text-sm text-muted-foreground'>No relations yet.</p>}
      {lines !== undefined && lines.length > 0 && (
        <ul aria-label='Relations' className='divide-y rounded-xl border'>
          {lines.map((line) => {
            const attitude = attitudeOf(line.intensity);
            return (
              <li key={line.id} className='flex min-h-12 items-center justify-between gap-3 px-3'>
                <span className='flex items-center gap-2'>
                  {line.colour !== null && <span aria-hidden className='size-2.5 rounded-full' style={{ backgroundColor: line.colour }} />}
                  {line.kind !== null && <span className='text-sm text-muted-foreground'>{line.kind.replaceAll('_', ' ')}</span>}
                  {line.href === null || line.name === null ? (
                    <span className='text-muted-foreground'>{line.name ?? 'Someone'}</span>
                  ) : (
                    <Link href={line.href} className='underline-offset-4 hover:underline'>
                      {line.name}
                    </Link>
                  )}
                  {line.mirrored && <ArrowLeftRight className='size-4 text-muted-foreground' aria-label='Mirrored' />}
                </span>
                {attitude !== null && (
                  <span className='tabular-nums text-sm' aria-label={`Attitude ${attitude}`}>
                    {attitude}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
