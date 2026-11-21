// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * A record's picture by link (fandom, wikis…): shown as it is, with no referrer (such sites refuse
 * hotlinks that send one), and for an editor a field to paste a new link or take it off.
 */
import NextImage from 'next/image';
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { Input } from 'zephyrex/ui/input';
import { LIMITS } from '../../contract';
import { WriteProblem } from './WriteProblem';

const PICTURE_PX = 512;

/** An image by link, never sending the wiki's address to the host. */
export function LinkedImage({ src, alt, className }: { src: string; alt: string; className?: string }): ReactElement {
  // unoptimized: Next's optimizer would fetch it itself (and need each host listed); the browser loads
  // it straight from the host, with no referrer.
  return <NextImage src={src} alt={alt} width={PICTURE_PX} height={PICTURE_PX} unoptimized referrerPolicy='no-referrer' className={className} />;
}

export function PicturePanel({
  name,
  url,
  onSave,
}: {
  /** The record's name, for the picture's description. */
  name: string;
  url: string | null | undefined;
  /** Given when the reader may change it; resolves to why it failed, or null. */
  onSave?: (next: string | null) => Promise<string | null>;
}): ReactElement | null {
  const id = useId();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(url ?? '');
  const [problem, setProblem] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const save = async (next: string | null): Promise<void> => {
    if (onSave === undefined) return;
    setSaving(true);
    const failed = await onSave(next);
    setSaving(false);
    setProblem(failed);
    if (failed === null) setEditing(false);
  };
  const submit = (event: FormEvent): void => {
    event.preventDefault();
    void save(draft.trim() === '' ? null : draft.trim());
  };
  if (!url && onSave === undefined) return null;
  return (
    <section aria-label='Picture' className='grid justify-items-start gap-2'>
      {url && <LinkedImage src={url} alt={`Picture of ${name}`} className='h-auto max-h-72 w-auto max-w-full rounded-md border object-contain' />}
      {editing ? (
        <form onSubmit={submit} className='grid w-full gap-2'>
          <label htmlFor={`${id}-link`} className='text-sm font-medium'>
            Picture link
          </label>
          <Input
            id={`${id}-link`}
            type='url'
            inputMode='url'
            value={draft}
            maxLength={LIMITS.picture_url_characters}
            placeholder='https://…'
            onChange={(event) => setDraft(event.target.value)}
          />
          <WriteProblem problem={problem} />
          <div className='flex flex-wrap gap-2'>
            <Button type='submit' disabled={saving}>
              {saving ? 'Saving…' : 'Save picture'}
            </Button>
            {url && (
              <Button type='button' variant='outline' disabled={saving} onClick={() => void save(null)}>
                Take it off
              </Button>
            )}
            <Button type='button' variant='ghost' onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        onSave !== undefined && (
          <Button type='button' size='sm' variant='ghost' onClick={() => setEditing(true)}>
            {url ? 'Change picture' : 'Add a picture by link'}
          </Button>
        )
      )}
    </section>
  );
}
