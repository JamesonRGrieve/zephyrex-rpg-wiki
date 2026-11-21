// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * A scenario's play styles (freeform, combat-heavy, mystery…): each a chip an editor can take off,
 * and a picker of the shared ones and one's own, or a new one by name. Shared ones are everyone's
 * to use; a new one is the person's own.
 */
import { X } from 'lucide-react';
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { Input } from 'zephyrex/ui/input';
import { LIMITS } from '../../contract';
import { WriteProblem } from './WriteProblem';

export interface PlayStyle {
  /** The link's id (entity_taxon). */
  id: string;
  name: string;
}

export interface PlayStyleOption {
  /** The taxon's id. */
  id: string;
  name: string;
}

export function PlayStyles({
  styles,
  options,
  onAdd,
  onCreate,
  onRemove,
  problem = null,
}: {
  styles: readonly PlayStyle[];
  /** Every play style one may use (shared and one's own); those already on are left out of the picker. */
  options: readonly PlayStyleOption[];
  onAdd?: (taxonId: string) => void;
  onCreate?: (name: string) => void;
  onRemove?: (style: PlayStyle) => void;
  problem?: string | null;
}): ReactElement {
  const id = useId();
  const [picked, setPicked] = useState('');
  const [name, setName] = useState('');
  const taken = new Set(styles.map((style) => style.name));
  const free = options.filter((option) => !taken.has(option.name));
  const canEdit = onAdd !== undefined && onCreate !== undefined && onRemove !== undefined;
  const create = (event: FormEvent): void => {
    event.preventDefault();
    if (name.trim() === '' || onCreate === undefined) return;
    onCreate(name.trim());
    setName('');
  };
  return (
    <section aria-labelledby={`${id}-title`} className='grid gap-3'>
      <h2 id={`${id}-title`} className='text-lg font-semibold'>
        Play style
      </h2>
      {styles.length === 0 ? (
        <p className='text-sm text-muted-foreground'>No play style yet.</p>
      ) : (
        <ul aria-label='Play styles' className='flex flex-wrap gap-2'>
          {styles.map((style) => (
            <li key={style.id} className='flex min-h-9 items-center gap-1 rounded-full border pl-3 pr-1 text-sm'>
              <span>{style.name}</span>
              {canEdit && (
                <Button type='button' variant='ghost' size='icon' className='size-8 rounded-full' aria-label={`Remove ${style.name}`} onClick={() => onRemove(style)}>
                  <X aria-hidden />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {canEdit && (
        <div className='flex flex-wrap items-end gap-3'>
          <div className='grid gap-1'>
            <label htmlFor={`${id}-pick`} className='text-sm font-medium'>
              Add a play style
            </label>
            <div className='flex gap-2'>
              <select
                id={`${id}-pick`}
                value={picked}
                onChange={(event) => setPicked(event.target.value)}
                className='h-10 rounded-md border border-input bg-background px-3 text-sm'
              >
                <option value=''>Choose…</option>
                {free.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
              <Button
                type='button'
                variant='outline'
                disabled={picked === ''}
                onClick={() => {
                  onAdd(picked);
                  setPicked('');
                }}
              >
                Add
              </Button>
            </div>
          </div>
          <form onSubmit={create} className='grid min-w-0 gap-1'>
            <label htmlFor={`${id}-new`} className='text-sm font-medium'>
              Or a new one
            </label>
            <div className='flex gap-2'>
              <Input id={`${id}-new`} value={name} maxLength={LIMITS.name_characters} placeholder='slow-burn' onChange={(event) => setName(event.target.value)} className='w-40' />
              <Button type='submit' variant='outline' disabled={name.trim() === ''}>
                Make it
              </Button>
            </div>
          </form>
        </div>
      )}
      <WriteProblem problem={problem} />
    </section>
  );
}
