// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * One place's or person's page body: its kind, where it sits, and its entry. The page above owns
 * the h1 (the record's name). The entry reads as its lines of text until the editor arrives (S5);
 * a record with none says how to start.
 */
import Link from 'next/link';
import type { ReactElement } from 'react';
import { plainText } from '~/lib/entry';
import { kindLabel } from './EntityList';

export interface EntityPageProps {
  kind: string | null;
  /** The entry's stored JSON text, if it has one. */
  entry: string | null;
  /** The plain-text copy, read when the entry can't be. */
  description: string | null;
  /** Where it is: a place's parent, or the place a person stands in. */
  where?: { label: string; name: string; href: string } | undefined;
}

/** The entry's lines: from the entry itself, else the stored plain text. */
export function linesOf(entry: string | null, description: string | null): string[] {
  if (entry !== null) {
    try {
      return plainText(JSON.parse(entry) as unknown).split('\n');
    } catch {
      // Unreadable: fall back to the plain-text copy the server kept.
    }
  }
  return description === null || description === '' ? [] : description.split('\n');
}

/** Each line with a key from its text and how often that text came before (lines can repeat). */
export function keyed(lines: readonly string[]): { key: string; line: string }[] {
  const seen = new Map<string, number>();
  return lines.map((line) => {
    const count = seen.get(line) ?? 0;
    seen.set(line, count + 1);
    return { key: `${count}:${line}`, line };
  });
}

export function EntityPage({ kind, entry, description, where }: EntityPageProps): ReactElement {
  const lines = linesOf(entry, description).filter((line) => line.trim() !== '');
  return (
    <article className='space-y-6'>
      {(kind !== null || where !== undefined) && (
        <dl className='grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm'>
          {kind !== null && (
            <>
              <dt className='text-muted-foreground'>Kind</dt>
              <dd>{kindLabel(kind)}</dd>
            </>
          )}
          {where !== undefined && (
            <>
              <dt className='text-muted-foreground'>{where.label}</dt>
              <dd>
                <Link href={where.href} className='underline underline-offset-4'>
                  {where.name}
                </Link>
              </dd>
            </>
          )}
        </dl>
      )}
      {lines.length === 0 ? (
        <p className='rounded-xl border border-dashed p-6 text-center text-muted-foreground'>Nothing written here yet.</p>
      ) : (
        <div className='max-w-prose space-y-3 font-serif text-lg leading-relaxed'>
          {keyed(lines).map(({ key, line }) => (
            <p key={key}>{line}</p>
          ))}
        </div>
      )}
    </article>
  );
}
