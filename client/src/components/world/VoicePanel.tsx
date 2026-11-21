// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * How the AI plays a person (S4c): personality, speech, a first message and example lines. It is
 * for the GM and the AI, never the players. Read as it stands; "Edit voice" opens a form whose
 * save says why it failed, if it did.
 */
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import type { Voice } from '~/lib/names';
import { WriteProblem } from './WriteProblem';

const PARTS = [
  { key: 'personality', label: 'Personality', hint: 'Who they are, as the AI should play them' },
  { key: 'speech', label: 'Speech', hint: 'How they talk: words, rhythm, habits' },
  { key: 'first_message', label: 'First message', hint: 'What they say when a scene opens on them' },
] as const;

const EMPTY: Voice = { personality: '', speech: '', first_message: '', examples: [] };

function VoiceForm({ voice, onSave, onDone }: { voice: Voice; onSave: (next: Voice) => Promise<string | null>; onDone: () => void }): ReactElement {
  const id = useId();
  const [draft, setDraft] = useState<Voice>(voice);
  const [examples, setExamples] = useState(voice.examples.join('\n\n'));
  const [problem, setProblem] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    setSaving(true);
    const failed = await onSave({ ...draft, examples: examples.split(/\n\s*\n/).map((one) => one.trim()).filter(Boolean) });
    setSaving(false);
    setProblem(failed);
    if (failed === null) onDone();
  };
  return (
    <form onSubmit={(event) => void submit(event)} className='grid gap-4'>
      {PARTS.map((part) => (
        <div key={part.key} className='grid gap-1'>
          <label htmlFor={`${id}-${part.key}`} className='text-sm font-medium'>
            {part.label}
          </label>
          <textarea
            id={`${id}-${part.key}`}
            value={draft[part.key]}
            onChange={(event) => setDraft({ ...draft, [part.key]: event.target.value })}
            rows={3}
            placeholder={part.hint}
            className='min-h-20 rounded-md border border-input bg-background px-3 py-2 text-sm'
          />
        </div>
      ))}
      <div className='grid gap-1'>
        <label htmlFor={`${id}-examples`} className='text-sm font-medium'>
          Example lines
        </label>
        <textarea
          id={`${id}-examples`}
          value={examples}
          onChange={(event) => setExamples(event.target.value)}
          rows={4}
          placeholder='A blank line between examples'
          className='min-h-24 rounded-md border border-input bg-background px-3 py-2 text-sm'
        />
      </div>
      <WriteProblem problem={problem} />
      <div className='flex gap-2'>
        <Button type='submit' disabled={saving}>
          {saving ? 'Saving…' : 'Save voice'}
        </Button>
        <Button type='button' variant='ghost' onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function VoicePanel({
  voice,
  canEdit = false,
  onSave,
}: {
  /** The person's voice, or null when they have none yet. */
  voice: Voice | null;
  canEdit?: boolean;
  onSave?: (next: Voice) => Promise<string | null>;
}): ReactElement {
  const [editing, setEditing] = useState(false);
  const shown = voice ?? EMPTY;
  const empty = PARTS.every((part) => shown[part.key] === '') && shown.examples.length === 0;
  return (
    <section aria-labelledby='voice-title' className='space-y-3'>
      <div className='flex items-center justify-between gap-3'>
        <h2 id='voice-title' className='text-lg font-semibold'>
          Voice
        </h2>
        {canEdit && onSave !== undefined && !editing && (
          <Button type='button' size='sm' variant='outline' onClick={() => setEditing(true)}>
            Edit voice
          </Button>
        )}
      </div>
      <p className='text-sm text-muted-foreground'>How the AI plays them. For the GM, never shown to players.</p>
      {editing && onSave !== undefined ? (
        <VoiceForm voice={shown} onSave={onSave} onDone={() => setEditing(false)} />
      ) : empty ? (
        <p className='text-sm text-muted-foreground'>No voice yet.</p>
      ) : (
        <dl className='grid gap-3'>
          {PARTS.filter((part) => shown[part.key] !== '').map((part) => (
            <div key={part.key} className='grid gap-1'>
              <dt className='text-sm font-medium'>{part.label}</dt>
              <dd className='whitespace-pre-line [overflow-wrap:anywhere]'>{shown[part.key]}</dd>
            </div>
          ))}
          {shown.examples.length > 0 && (
            <div className='grid gap-1'>
              <dt className='text-sm font-medium'>Example lines</dt>
              <dd>
                <ul className='grid gap-2'>
                  {shown.examples.map((line) => (
                    // A voice keeps each example line once, so the line is its key.
                    <li key={line} className='whitespace-pre-line rounded-md border px-3 py-2 [overflow-wrap:anywhere]'>
                      {line}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}
