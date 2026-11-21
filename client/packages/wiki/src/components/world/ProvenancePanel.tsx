// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * Where a scenario or record came from: homebrew, official (as published) or adapted (from a
 * published one), and its source (title, publisher, product or page). Read as a line; "Edit origin"
 * opens a small form whose save says why it failed, if it did. A homebrew one has no source.
 */
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { Input } from 'zephyrex/ui/input';
import { LIMITS, PROVENANCES } from '../../contract';
import { HOMEBREW, type Provenance } from '../../lib/provenance';
import { WriteProblem } from './WriteProblem';

const LABELS: Record<string, string> = { homebrew: 'Homebrew', official: 'Official', adapted: 'Adapted' };
const labelOf = (provenance: string): string => LABELS[provenance] ?? provenance;

function OriginForm({ origin, onSave, onDone }: { origin: Provenance; onSave: (next: Provenance) => Promise<string | null>; onDone: () => void }): ReactElement {
  const id = useId();
  const [kind, setKind] = useState(origin.provenance);
  const [source, setSource] = useState(origin.source ?? '');
  const [problem, setProblem] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const homebrew = kind === HOMEBREW;
  const submit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    setSaving(true);
    const failed = await onSave({ provenance: kind, source: homebrew || source.trim() === '' ? null : source.trim() });
    setSaving(false);
    setProblem(failed);
    if (failed === null) onDone();
  };
  return (
    <form onSubmit={(event) => void submit(event)} className='grid gap-3'>
      <div className='flex flex-wrap items-end gap-3'>
        <div className='grid gap-1'>
          <label htmlFor={`${id}-kind`} className='text-sm font-medium'>
            Origin
          </label>
          <select
            id={`${id}-kind`}
            value={kind}
            onChange={(event) => setKind(event.target.value)}
            className='h-10 rounded-md border border-input bg-background px-3 text-sm'
          >
            {PROVENANCES.map((one) => (
              <option key={one} value={one}>
                {labelOf(one)}
              </option>
            ))}
          </select>
        </div>
        <div className='grid min-w-0 flex-1 gap-1'>
          <label htmlFor={`${id}-source`} className='text-sm font-medium'>
            Source
          </label>
          <Input
            id={`${id}-source`}
            value={homebrew ? '' : source}
            disabled={homebrew}
            maxLength={LIMITS.source_characters}
            placeholder={homebrew ? 'Homebrew has no source' : 'Title, publisher, product or page'}
            onChange={(event) => setSource(event.target.value)}
          />
        </div>
      </div>
      <WriteProblem problem={problem} />
      <div className='flex gap-2'>
        <Button type='submit' disabled={saving}>
          {saving ? 'Saving…' : 'Save origin'}
        </Button>
        <Button type='button' variant='ghost' onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function ProvenancePanel({
  provenance,
  source,
  onSave,
}: {
  /** Its provenance; none reads as homebrew (a record stored before provenance existed). */
  provenance: string | null | undefined;
  source: string | null | undefined;
  /** Given when the reader may change it. */
  onSave?: (next: Provenance) => Promise<string | null>;
}): ReactElement {
  const [editing, setEditing] = useState(false);
  const origin: Provenance = { provenance: provenance ?? HOMEBREW, source: source ?? null };
  if (editing && onSave !== undefined) return <OriginForm origin={origin} onSave={onSave} onDone={() => setEditing(false)} />;
  return (
    <div className='flex flex-wrap items-center gap-x-3 gap-y-1 text-sm'>
      <span className='text-muted-foreground'>Origin</span>
      <span className='rounded-full border px-2.5 py-0.5 font-medium'>{labelOf(origin.provenance)}</span>
      {origin.source !== null && <span className='min-w-0 [overflow-wrap:anywhere]'>{origin.source}</span>}
      {onSave !== undefined && (
        <Button type='button' size='sm' variant='ghost' onClick={() => setEditing(true)}>
          Edit origin
        </Button>
      )}
    </div>
  );
}
