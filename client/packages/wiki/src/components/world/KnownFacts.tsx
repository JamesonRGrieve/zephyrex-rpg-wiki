// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * What the player characters have learned about a record (operator, 2026-11-24: "only player visible
 * information and learned facts"). For the GM: who knows what, each fact removable, and a new one
 * added for a character (with no text: they know of it, which opens a record kept to the GM to
 * them). For a player: what their character knows, read only. Four states, as every data view.
 */
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { Input } from 'zephyrex/ui/input';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { LIMITS } from '../../contract';
import { WriteProblem } from './WriteProblem';

export interface KnownFactLine {
  id: string;
  /** Who knows it (the GM's view), or null in a player's own view. */
  who: string | null;
  /** What they learned, or null: they know of it. */
  text: string | null;
}

export interface KnownFactsProps {
  /** The section's heading: "Who knows", or "What <character> knows". */
  title: string;
  lines: readonly KnownFactLine[] | undefined;
  error?: Error;
  onRetry?: () => Promise<unknown>;
  /** The characters a new fact can be for (the GM's view); none to offer, no form. */
  characters?: readonly { id: string; name: string }[];
  onAdd?: (personId: string, text: string) => Promise<string | null>;
  onRemove?: (line: KnownFactLine) => void;
  problem?: string | null;
}

function AddFact({ characters, onAdd }: { characters: readonly { id: string; name: string }[]; onAdd: (personId: string, text: string) => Promise<string | null> }): ReactElement {
  const id = useId();
  const [personId, setPersonId] = useState(characters[0]?.id ?? '');
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const submit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    setSaving(true);
    const failed = await onAdd(personId, text);
    setSaving(false);
    setProblem(failed);
    if (failed === null) setText('');
  };
  return (
    <form onSubmit={(event) => void submit(event)} className='grid gap-3' aria-label='Add a known fact'>
      <div className='flex flex-wrap items-end gap-3'>
        <div className='grid gap-1'>
          <label htmlFor={`${id}-who`} className='text-sm font-medium'>
            Character
          </label>
          <select
            id={`${id}-who`}
            value={personId}
            onChange={(event) => setPersonId(event.target.value)}
            className='h-10 rounded-md border border-input bg-background px-3 text-sm'
          >
            {characters.map((one) => (
              <option key={one.id} value={one.id}>
                {one.name}
              </option>
            ))}
          </select>
        </div>
        <div className='grid min-w-0 flex-1 gap-1'>
          <label htmlFor={`${id}-text`} className='text-sm font-medium'>
            What they learned
          </label>
          <Input
            id={`${id}-text`}
            value={text}
            maxLength={LIMITS.known_fact_characters}
            placeholder='Leave empty: they know of it'
            onChange={(event) => setText(event.target.value)}
          />
        </div>
      </div>
      <WriteProblem problem={problem} />
      <div>
        <Button type='submit' disabled={saving || personId === ''}>
          {saving ? 'Saving…' : 'Add known fact'}
        </Button>
      </div>
    </form>
  );
}

export function KnownFacts({ title, lines, error, onRetry, characters, onAdd, onRemove, problem = null }: KnownFactsProps): ReactElement {
  const heading = useId();
  return (
    <section aria-labelledby={heading} className='space-y-3'>
      <h2 id={heading} className='text-lg font-semibold'>
        {title}
      </h2>
      {error !== undefined && <LoadProblem what='what is known' error={error} onRetry={onRetry} />}
      {lines === undefined && error === undefined && <SkeletonRows rows={2} label='Loading what is known' />}
      {lines !== undefined && lines.length === 0 && <p className='text-sm text-muted-foreground'>Nothing learned yet.</p>}
      {lines !== undefined && lines.length > 0 && (
        <ul aria-label={title} className='divide-y rounded-xl border'>
          {lines.map((line) => (
            <li key={line.id} className='flex items-start justify-between gap-3 px-3 py-2'>
              <p className='min-w-0 [overflow-wrap:anywhere]'>
                {line.who !== null && <span className='font-medium'>{`${line.who}: `}</span>}
                {line.text ?? <span className='text-muted-foreground'>Knows of it</span>}
              </p>
              {onRemove !== undefined && (
                <Button type='button' size='sm' variant='ghost' onClick={() => onRemove(line)} aria-label={`Remove ${line.who === null ? 'this fact' : `${line.who}'s fact`}`}>
                  Remove
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      <WriteProblem problem={problem} />
      {onAdd !== undefined && characters !== undefined && characters.length > 0 && <AddFact characters={characters} onAdd={onAdd} />}
    </section>
  );
}
