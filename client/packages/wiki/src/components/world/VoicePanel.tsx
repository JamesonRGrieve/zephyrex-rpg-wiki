// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * How the AI plays a person (S4c): personality, speech, a first message and example lines, and
 * (Parity, a SillyTavern card's own) a system prompt, post-history instructions, a Character's Note,
 * talkativeness and across chats. It is for the GM and the AI, never the players. Read as it stands; "Edit voice" opens a form whose
 * save says why it failed, if it did.
 */
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { Input } from 'zephyrex/ui/input';
import { DEPTH_PROMPT_ROLES, LIMITS, VOICE_DEFAULTS } from '../../contract';
import { type DepthPrompt, voice as filledVoice, type Voice } from '../../lib/names';
import { WriteProblem } from './WriteProblem';

const PARTS = [
  { key: 'personality', label: 'Personality', hint: 'Who they are, as the AI should play them' },
  { key: 'speech', label: 'Speech', hint: 'How they talk: words, rhythm, habits' },
  { key: 'first_message', label: 'First message', hint: 'What they say when a scene opens on them' },
] as const;
/** The prompt parts a SillyTavern card carries, shown after the example lines. */
const PROMPTS = [
  { key: 'system_prompt', label: 'System prompt', hint: 'Replaces the main prompt while they speak' },
  { key: 'post_history_instructions', label: 'Post-history instructions', hint: 'Sent after the chat history' },
] as const;
const FIELD = 'min-h-20 rounded-md border border-input bg-background px-3 py-2 text-sm';
const NO_NOTE: DepthPrompt = { prompt: '', depth: VOICE_DEFAULTS.depth_prompt_depth, role: VOICE_DEFAULTS.depth_prompt_role };

// Every part at its empty value or default, as the contract fills a voice given nothing.
const EMPTY: Voice = filledVoice({});

function VoiceForm({ voice, onSave, onDone }: { voice: Voice; onSave: (next: Voice) => Promise<string | null>; onDone: () => void }): ReactElement {
  const id = useId();
  const [draft, setDraft] = useState<Voice>(voice);
  const [examples, setExamples] = useState(voice.examples.join('\n\n'));
  const [note, setNote] = useState<DepthPrompt>(voice.depth_prompt ?? NO_NOTE);
  const [problem, setProblem] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    setSaving(true);
    const failed = await onSave({
      ...draft,
      examples: examples.split(/\n\s*\n/).map((one) => one.trim()).filter(Boolean),
      depth_prompt: note.prompt.trim() === '' ? null : note,
    });
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
            className={FIELD}
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
      {PROMPTS.map((part) => (
        <div key={part.key} className='grid gap-1'>
          <label htmlFor={`${id}-${part.key}`} className='text-sm font-medium'>
            {part.label}
          </label>
          <textarea
            id={`${id}-${part.key}`}
            value={draft[part.key]}
            onChange={(event) => setDraft({ ...draft, [part.key]: event.target.value })}
            rows={2}
            placeholder={part.hint}
            className={FIELD}
          />
        </div>
      ))}
      <fieldset className='grid gap-2 rounded-md border p-3'>
        <legend className='px-1 text-sm font-medium'>Character&apos;s note</legend>
        <label htmlFor={`${id}-note`} className='sr-only'>
          Character&apos;s note
        </label>
        <textarea
          id={`${id}-note`}
          value={note.prompt}
          onChange={(event) => setNote({ ...note, prompt: event.target.value })}
          rows={2}
          placeholder='Placed in the chat a few messages up, every turn'
          className={FIELD}
        />
        <div className='flex flex-wrap gap-3'>
          <div className='grid gap-1'>
            <label htmlFor={`${id}-depth`} className='text-sm'>
              Depth
            </label>
            <Input
              id={`${id}-depth`}
              type='number'
              min={0}
              max={LIMITS.depth_prompt_depth}
              value={note.depth}
              onChange={(event) => setNote({ ...note, depth: Number(event.target.value) })}
              className='w-24'
            />
          </div>
          <div className='grid gap-1'>
            <label htmlFor={`${id}-role`} className='text-sm'>
              As
            </label>
            <select
              id={`${id}-role`}
              value={note.role}
              onChange={(event) => setNote({ ...note, role: event.target.value })}
              className='h-10 rounded-md border border-input bg-background px-3 text-sm'
            >
              {DEPTH_PROMPT_ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </div>
        </div>
      </fieldset>
      <div className='flex flex-wrap items-end gap-4'>
        <div className='grid gap-1'>
          <label htmlFor={`${id}-talkativeness`} className='text-sm font-medium'>
            Talkativeness
          </label>
          <Input
            id={`${id}-talkativeness`}
            type='number'
            min={0}
            max={1}
            step={0.05}
            value={draft.talkativeness}
            onChange={(event) => setDraft({ ...draft, talkativeness: Number(event.target.value) })}
            className='w-24'
          />
        </div>
        <label className='flex min-h-10 items-center gap-2 text-sm'>
          <input
            type='checkbox'
            checked={draft.across_chats}
            onChange={(event) => setDraft({ ...draft, across_chats: event.target.checked })}
            className='size-4'
          />
          Across chats
        </label>
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
  const empty =
    [...PARTS, ...PROMPTS].every((part) => shown[part.key] === '') && shown.examples.length === 0 && shown.depth_prompt === null;
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
          {PROMPTS.filter((part) => shown[part.key] !== '').map((part) => (
            <div key={part.key} className='grid gap-1'>
              <dt className='text-sm font-medium'>{part.label}</dt>
              <dd className='whitespace-pre-line [overflow-wrap:anywhere]'>{shown[part.key]}</dd>
            </div>
          ))}
          {shown.depth_prompt !== null && (
            <div className='grid gap-1'>
              <dt className='text-sm font-medium'>Character&apos;s note</dt>
              <dd className='whitespace-pre-line [overflow-wrap:anywhere]'>{shown.depth_prompt.prompt}</dd>
              <dd className='text-sm text-muted-foreground'>{`Depth ${shown.depth_prompt.depth}, as ${shown.depth_prompt.role}`}</dd>
            </div>
          )}
          <div className='grid gap-1'>
            <dt className='text-sm font-medium'>Talkativeness</dt>
            <dd>{`${shown.talkativeness}${shown.across_chats ? ' · across chats' : ''}`}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
