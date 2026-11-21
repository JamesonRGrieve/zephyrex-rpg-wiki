// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A record's status and taxa (W6): tags, categories, races and the rest, each a chip in its own
 * colour, linked to the world's taxonomy. Read-only here. Four states, as every data view.
 */
import Link from 'next/link';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';

export interface Chip {
  id: string;
  /** The taxon's or status's name, or null while it loads (or if it's gone). */
  name: string | null;
  colour: string | null;
  kind: string | null;
  href: string | null;
}

export interface TaxonChipsProps {
  status: Chip | null | undefined;
  taxa: readonly Chip[] | undefined;
  error?: Error;
  onRetry?: () => Promise<unknown>;
}

function Swatch({ colour }: { colour: string | null }): ReactElement | null {
  return colour === null ? null : <span aria-hidden className='size-2.5 rounded-full' style={{ backgroundColor: colour }} />;
}

function ChipView({ chip }: { chip: Chip }): ReactElement {
  const body = (
    <>
      <Swatch colour={chip.colour} />
      <span>{chip.name ?? 'Unnamed'}</span>
      {/* A real space, so the link reads "Elf race", not "Elfrace". */}
      {chip.kind !== null && chip.kind !== 'tag' && (
        <>
          {' '}
          <span className='text-xs text-muted-foreground'>{chip.kind.replaceAll('_', ' ')}</span>
        </>
      )}
    </>
  );
  // 44 px tap targets (UX and UI: mobile).
  const className = 'inline-flex min-h-11 items-center gap-1.5 rounded-full border px-3 text-sm';
  return chip.href === null ? (
    <span className={className}>{body}</span>
  ) : (
    <Link href={chip.href} className={`${className} hover:bg-accent`}>
      {body}
    </Link>
  );
}

export function TaxonChips({ status, taxa, error, onRetry }: TaxonChipsProps): ReactElement {
  const loading = (status === undefined || taxa === undefined) && error === undefined;
  return (
    <section aria-labelledby='taxa-title' className='space-y-2'>
      <h2 id='taxa-title' className='text-lg font-semibold'>
        Classification
      </h2>
      {error !== undefined && <LoadProblem what='this record’s tags' error={error} onRetry={onRetry} />}
      {loading && <SkeletonRows rows={1} label='Loading the tags' />}
      {!loading && error === undefined && status !== undefined && taxa !== undefined && (
        <div className='flex flex-wrap items-center gap-2'>
          {status !== null && (
            <p className='inline-flex items-center gap-1.5 text-sm'>
              <span className='text-muted-foreground'>Status:</span>
              <ChipView chip={status} />
            </p>
          )}
          {taxa.length === 0 && status === null && <p className='text-sm text-muted-foreground'>No tags or status yet.</p>}
          {taxa.length > 0 && (
            <ul aria-label='Tags' className='flex flex-wrap gap-2'>
              {taxa.map((chip) => (
                <li key={chip.id}>
                  <ChipView chip={chip} />
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
