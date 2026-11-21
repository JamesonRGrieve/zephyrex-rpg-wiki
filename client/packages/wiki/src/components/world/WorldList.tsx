// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * The person's worlds (rpg_core's campaigns): each opens its places, a new one takes only a name,
 * and deleting one offers an undo. Four states: loading, a load failure with a retry, a first
 * world to make, and the worlds.
 */
import { Globe, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { type ReactElement, useId, useState } from 'react';
import { deferWithUndo } from 'zephyrex/hooks/useToast';
import { useHidden } from 'zephyrex/hooks/useWrites';
import { Button } from 'zephyrex/ui/button';
import { Input } from 'zephyrex/ui/input';
import { Label } from 'zephyrex/ui/label';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { LIMITS } from '../../contract';
import type { World } from '../../features/data/records';
import { idOf } from '../../features/data/records';
import { WriteProblem } from './WriteProblem';
import { useWikiBase } from '../../base';
import { kindPath } from '../../lib/paths';
import { HOMEBREW } from '../../lib/provenance';

export function WorldList({
  worlds,
  error,
  onRetry,
  onCreate,
  onDelete,
  problem = null,
}: {
  worlds: readonly World[] | undefined;
  error?: Error;
  onRetry?: () => Promise<unknown>;
  /** Makes a world; resolves true when it landed. */
  onCreate: (name: string) => Promise<boolean>;
  onDelete: (world: World) => void;
  problem?: string | null;
}): ReactElement {
  const base = useWikiBase();
  const [name, setName] = useState('');
  const nameId = useId();
  const hidden = useHidden(worlds ?? [], idOf);

  return (
    <div className='space-y-4'>
      <form
        className='flex flex-wrap items-end gap-2'
        onSubmit={(event) => {
          event.preventDefault();
          void onCreate(name.trim()).then((made) => made && setName(''));
        }}
      >
        <div className='grid min-w-0 flex-1 gap-1.5'>
          <Label htmlFor={nameId}>New world</Label>
          <Input
            id={nameId}
            value={name}
            maxLength={LIMITS.name_characters}
            className='h-11'
            placeholder='The Salt Coast'
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <Button type='submit' className='h-11' disabled={name.trim() === ''}>
          Make it
        </Button>
      </form>
      <WriteProblem problem={problem} />
      {error !== undefined && <LoadProblem what='your worlds' error={error} onRetry={onRetry} />}
      {worlds === undefined && error === undefined && <SkeletonRows rows={3} label='Loading your worlds' />}
      {worlds !== undefined && hidden.shown.length === 0 && !hidden.pending && (
        <p className='rounded-xl border border-dashed p-8 text-center text-muted-foreground'>
          No worlds yet. Name one above to start writing it down.
        </p>
      )}
      {hidden.shown.length > 0 && (
        <ul aria-label='Your worlds' className='divide-y rounded-xl border'>
          {hidden.shown.map((world) => (
            <li key={world.id} className='group flex items-center gap-3 p-2'>
              <Link
                href={kindPath(base, world.id, 'location')}
                className='flex min-h-12 min-w-0 flex-1 items-center gap-3 rounded-md px-2 hover:bg-accent'
              >
                <Globe className='size-4 shrink-0 text-muted-foreground' aria-hidden />
                <span className='min-w-0'>
                  <span className='flex min-w-0 items-center gap-2'>
                    <span className='truncate font-medium'>{world.name}</span>
                    {world.provenance !== undefined && world.provenance !== null && world.provenance !== HOMEBREW && (
                      <span className='shrink-0 rounded-full border px-2 py-0.5 text-xs capitalize'>{world.provenance}</span>
                    )}
                  </span>
                  {world.description !== null && world.description !== '' && (
                    <span className='block truncate text-xs text-muted-foreground'>{world.description}</span>
                  )}
                </span>
              </Link>
              <Button
                type='button'
                variant='ghost'
                size='icon'
                className='size-11 pointer-fine:opacity-0 pointer-fine:group-hover:opacity-100 pointer-fine:group-focus-within:opacity-100'
                aria-label={`Delete ${world.name}`}
                onClick={() => {
                  hidden.hide([world.id]);
                  deferWithUndo(
                    `${world.name} deleted`,
                    () => onDelete(world),
                    () => hidden.show([world.id]),
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
  );
}
