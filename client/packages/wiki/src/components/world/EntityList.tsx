// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * One world's places or people: found by name or text, made with a name and a kind, opened to their
 * own page, and deleted with an undo. Four states: loading, a load failure with a retry, a first
 * one to make, and the list (or "nothing matches" for a search).
 */
import { Search, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { type ReactElement, type ReactNode, useId, useState } from 'react';
import { deferWithUndo } from 'zephyrex/hooks/useToast';
import { useHidden } from 'zephyrex/hooks/useWrites';
import { Button } from 'zephyrex/ui/button';
import { Input } from 'zephyrex/ui/input';
import { Label } from 'zephyrex/ui/label';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { LIMITS } from '../../contract';
import { idOf } from '../../features/data/records';
import { WriteProblem } from './WriteProblem';

export interface EntityRow {
  id: string;
  name: string;
  description: string | null;
  kind: string | null;
  /** A template (S4b, W7): copied into worlds, never a world fact. */
  is_template?: boolean | null;
}

/** A kind as people read it ("body_part" → "body part"). */
export const kindLabel = (kind: string): string => kind.replaceAll('_', ' ');

/** The rows whose name or text holds every word of the search, case aside. */
export function matching<T extends EntityRow>(rows: readonly T[], search: string): T[] {
  const words = search.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return [...rows];
  return rows.filter((row) => {
    const haystack = `${row.name}\n${row.description ?? ''}`.toLowerCase();
    return words.every((word) => haystack.includes(word));
  });
}

export function EntityList<T extends EntityRow>({
  what,
  plural,
  rows,
  error,
  onRetry,
  kinds,
  hrefOf,
  onCreate,
  onDelete,
  problem = null,
  aside,
}: {
  /** One of them, as a sentence names it ("place"). */
  what: string;
  /** Several ("places"). */
  plural: string;
  rows: readonly T[] | undefined;
  error?: Error;
  onRetry?: () => Promise<unknown>;
  kinds: readonly string[];
  hrefOf: (row: T) => string;
  /** Makes one; resolves true when it landed. */
  onCreate: (fields: { name: string; kind: string | null }) => Promise<boolean>;
  onDelete: (row: T) => void;
  problem?: string | null;
  /** Shown beside the list on a wide screen (the places' tree). */
  aside?: ReactNode;
}): ReactElement {
  const [search, setSearch] = useState('');
  const [name, setName] = useState('');
  const [kind, setKind] = useState('');
  const ids = { search: useId(), name: useId(), kind: useId() };
  const hidden = useHidden(rows ?? [], idOf);
  const shown = matching(hidden.shown, search);

  return (
    <div className='grid gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]'>
      <div className='min-w-0 space-y-4'>
        <form
          aria-label={`Add a ${what}`}
          className='flex flex-wrap items-end gap-2'
          onSubmit={(event) => {
            event.preventDefault();
            void onCreate({ name: name.trim(), kind: kind === '' ? null : kind }).then((made) => made && setName(''));
          }}
        >
          <div className='grid min-w-0 flex-1 basis-48 gap-1.5'>
            <Label htmlFor={ids.name}>{`New ${what}`}</Label>
            <Input
              id={ids.name}
              value={name}
              maxLength={LIMITS.name_characters}
              className='h-11'
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className='grid gap-1.5'>
            <Label htmlFor={ids.kind}>Kind</Label>
            <select
              id={ids.kind}
              value={kind}
              className='h-11 rounded-md border bg-background px-3 text-sm'
              onChange={(event) => setKind(event.target.value)}
            >
              <option value=''>Any</option>
              {kinds.map((one) => (
                <option key={one} value={one}>
                  {kindLabel(one)}
                </option>
              ))}
            </select>
          </div>
          <Button type='submit' className='h-11' disabled={name.trim() === ''}>
            Add
          </Button>
        </form>
        <WriteProblem problem={problem} />
        <div className='grid gap-1.5'>
          <Label htmlFor={ids.search} className='sr-only'>
            {`Find ${plural}`}
          </Label>
          <div className='relative'>
            <Search className='pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground' aria-hidden />
            <Input
              id={ids.search}
              type='search'
              value={search}
              placeholder={`Find ${plural}`}
              className='h-11 pl-9'
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>
        {error !== undefined && <LoadProblem what={`the ${plural}`} error={error} onRetry={onRetry} />}
        {rows === undefined && error === undefined && <SkeletonRows rows={4} label={`Loading ${plural}`} />}
        {rows !== undefined && hidden.shown.length === 0 && !hidden.pending && (
          <p className='rounded-xl border border-dashed p-8 text-center text-muted-foreground'>
            {`No ${plural} here yet. Add the first one above.`}
          </p>
        )}
        {hidden.shown.length > 0 && shown.length === 0 && (
          <p className='p-4 text-center text-muted-foreground'>{`No ${plural} match “${search.trim()}”.`}</p>
        )}
        {shown.length > 0 && (
          <ul aria-label={plural.charAt(0).toUpperCase() + plural.slice(1)} className='divide-y rounded-xl border'>
            {shown.map((row) => (
              <li key={row.id} className='group flex items-center gap-3 p-2'>
                <Link href={hrefOf(row)} className='flex min-h-12 min-w-0 flex-1 flex-col justify-center rounded-md px-2 hover:bg-accent'>
                  <span className='flex items-center gap-2'>
                    <span className='truncate font-medium'>{row.name}</span>
                    {/* A real space, so the link reads "Saltmarsh city", not "Saltmarshcity". */}
                    {row.kind !== null && (
                      <>
                        {' '}
                        <span className='shrink-0 text-xs text-muted-foreground'>{kindLabel(row.kind)}</span>
                      </>
                    )}
                    {row.is_template === true && (
                      <>
                        {' '}
                        <span className='shrink-0 rounded-md border px-1.5 text-xs font-medium'>Template</span>
                      </>
                    )}
                  </span>
                  {row.description !== null && row.description !== '' && (
                    <span className='block truncate text-xs text-muted-foreground'>{row.description}</span>
                  )}
                </Link>
                <Button
                  type='button'
                  variant='ghost'
                  size='icon'
                  className='size-11 pointer-fine:opacity-0 pointer-fine:group-hover:opacity-100 pointer-fine:group-focus-within:opacity-100'
                  aria-label={`Delete ${row.name}`}
                  onClick={() => {
                    hidden.hide([row.id]);
                    deferWithUndo(
                      `${row.name} deleted`,
                      () => onDelete(row),
                      () => hidden.show([row.id]),
                    );
                  }}
                >
                  <Trash2 aria-hidden />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {aside !== undefined && <aside className='min-w-0'>{aside}</aside>}
    </div>
  );
}
