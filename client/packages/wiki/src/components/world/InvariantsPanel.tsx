// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * A person's invariants (operator, 2026-11-28: NPCs get character invariants, lines they never cross,
 * "never harms a child", "never breaks a sworn oath"): the story holds their turns to them. For the
 * GM, never the players. Read as a list; "Edit lines" opens a form, one line per invariant, whose
 * save says why it failed, if it did.
 */
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { LIMITS } from '../../contract';
import { WriteProblem } from './WriteProblem';

function InvariantsForm({ lines, onSave, onDone }: { lines: string[]; onSave: (next: string[]) => Promise<string | null>; onDone: () => void }): ReactElement {
  const id = useId();
  const [draft, setDraft] = useState(lines.join('\n'));
  const [problem, setProblem] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    setSaving(true);
    const failed = await onSave(draft.split('\n').map((one) => one.trim()).filter(Boolean));
    setSaving(false);
    setProblem(failed);
    if (failed === null) onDone();
  };
  return (
    <form onSubmit={(event) => void submit(event)} className='grid gap-4'>
      <div className='grid gap-1'>
        <label htmlFor={`${id}-lines`} className='text-sm font-medium'>
          Lines they never cross
        </label>
        <textarea
          id={`${id}-lines`}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={4}
          placeholder={'Never harms a child\nNever breaks a sworn oath'}
          aria-describedby={`${id}-hint`}
          className='min-h-24 rounded-md border border-input bg-background px-3 py-2 text-sm'
        />
        <p id={`${id}-hint`} className='text-sm text-muted-foreground'>
          {`One per line, a short sentence each: at most ${LIMITS.invariants} of ${LIMITS.invariant_characters} characters.`}
        </p>
      </div>
      <WriteProblem problem={problem} />
      <div className='flex flex-wrap gap-2'>
        <Button type='submit' disabled={saving}>
          {saving ? 'Saving…' : 'Save lines'}
        </Button>
        <Button type='button' variant='ghost' onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function InvariantsPanel({
  invariants,
  canEdit = false,
  onSave,
}: {
  /** The person's invariants, in the order given. */
  invariants: string[];
  canEdit?: boolean;
  /** Saves the whole list; resolves to why it failed, or null. */
  onSave?: (next: string[]) => Promise<string | null>;
}): ReactElement {
  const [editing, setEditing] = useState(false);
  return (
    <section aria-labelledby='invariants-title' className='space-y-3'>
      <div className='flex items-center justify-between gap-3'>
        <h2 id='invariants-title' className='text-lg font-semibold'>
          Never crosses
        </h2>
        {canEdit && onSave !== undefined && !editing && (
          <Button type='button' size='sm' variant='outline' onClick={() => setEditing(true)}>
            Edit lines
          </Button>
        )}
      </div>
      <p className='text-sm text-muted-foreground'>The story holds their turns to these. For the GM, never shown to players.</p>
      {editing && onSave !== undefined ? (
        <InvariantsForm lines={invariants} onSave={onSave} onDone={() => setEditing(false)} />
      ) : invariants.length === 0 ? (
        <p className='text-sm text-muted-foreground'>No lines yet.</p>
      ) : (
        <ul className='grid gap-2'>
          {invariants.map((line) => (
            // Each line is kept once, so the line is its key.
            <li key={line} className='rounded-md border px-3 py-2 [overflow-wrap:anywhere]'>
              {line}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
