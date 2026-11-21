// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * A world as a scenario (copy on start): a scenario is never played; starting it makes a
 * playthrough, a new world with its own copy of every record. A playthrough links back to its
 * scenario.
 */
import Link from 'next/link';
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { Input } from 'zephyrex/ui/input';
import { LIMITS } from '../../contract';
import { WriteProblem } from './WriteProblem';

export function ScenarioPanel({
  isScenario,
  scenario,
  onStart,
}: {
  isScenario: boolean;
  /** For a playthrough: its scenario's name and page. */
  scenario?: { name: string; href: string } | null;
  /** Starts a playthrough; resolves to why it failed, or null. */
  onStart?: (name: string | null) => Promise<string | null>;
}): ReactElement | null {
  const id = useId();
  const [name, setName] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  if (!isScenario && !scenario) return null;
  const submit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    if (onStart === undefined) return;
    setStarting(true);
    const failed = await onStart(name.trim() === '' ? null : name.trim());
    setStarting(false);
    setProblem(failed);
  };
  return (
    <section aria-labelledby={`${id}-title`} className='grid gap-2'>
      <h2 id={`${id}-title`} className='text-lg font-semibold'>
        {isScenario ? 'Scenario' : 'Playthrough'}
      </h2>
      {isScenario ? (
        <>
          <p className='text-sm text-muted-foreground'>Play never changes a scenario: starting it makes a new campaign with its own copy of everything here.</p>
          {onStart !== undefined && (
            <form onSubmit={(event) => void submit(event)} className='flex flex-wrap items-end gap-2'>
              <div className='grid min-w-0 gap-1'>
                <label htmlFor={`${id}-name`} className='text-sm font-medium'>
                  Name of the playthrough
                </label>
                <Input id={`${id}-name`} value={name} maxLength={LIMITS.name_characters} placeholder='Run 1' onChange={(event) => setName(event.target.value)} className='w-56' />
              </div>
              <Button type='submit' disabled={starting}>
                {starting ? 'Starting…' : 'Start a playthrough'}
              </Button>
            </form>
          )}
          <WriteProblem problem={problem} />
        </>
      ) : (
        scenario && (
          <p className='text-sm'>
            {'A playthrough of '}
            <Link href={scenario.href} className='underline underline-offset-4'>
              {scenario.name}
            </Link>
          </p>
        )
      )}
    </section>
  );
}
