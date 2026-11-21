// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * A record's properties (S4b, W4): its own key/values, each read by its type, private ones marked.
 * Someone who may edit the record changes a value where it stands, flips a yes/no, adds a key and
 * removes one. Four states, as every data view.
 */
import { Lock, Trash2 } from 'lucide-react';
import { type FormEvent, type ReactElement, useId, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { InlineText } from 'zephyrex/ui/inline-text';
import { Input } from 'zephyrex/ui/input';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { PROPERTY_VALUE_TYPES } from '~/contract';
import { WriteProblem } from './WriteProblem';

export interface PropertyRow {
  id: string;
  key: string;
  value: string | null;
  value_type: string | null;
  is_private: boolean;
}

const TYPE_WORDS: Record<string, string> = { text: 'Text', number: 'Number', boolean: 'Yes or no', date: 'Date', link: 'Link' };

/** Only a page of this app or a web address is followed; anything else shows as text. */
function safeHref(value: string): string | null {
  if (value.startsWith('/') && !value.startsWith('//')) return value;
  return /^https?:\/\//i.test(value) ? value : null;
}

function Value({ row }: { row: PropertyRow }): ReactElement {
  if (row.value === null || row.value === '') return <span className='text-muted-foreground'>Not set</span>;
  if (row.value_type === 'boolean') return <span>{row.value === 'true' ? 'Yes' : 'No'}</span>;
  if (row.value_type === 'number') return <span className='tabular-nums'>{row.value}</span>;
  if (row.value_type === 'link') {
    const href = safeHref(row.value);
    return href === null ? (
      <span className='[overflow-wrap:anywhere]'>{row.value}</span>
    ) : (
      <a href={href} className='underline underline-offset-4 [overflow-wrap:anywhere]' rel='noopener noreferrer' target={href.startsWith('/') ? undefined : '_blank'}>
        {row.value}
      </a>
    );
  }
  return <span className='[overflow-wrap:anywhere]'>{row.value}</span>;
}

function EditValue<T extends PropertyRow>({ row, onSave }: { row: T; onSave: (row: T, value: string) => Promise<string | null> }): ReactElement {
  if (row.value_type === 'boolean') {
    const on = row.value === 'true';
    return (
      <Button type='button' size='sm' variant='outline' aria-pressed={on} aria-label={`${on ? 'Yes' : 'No'}: ${row.key}`} onClick={() => void onSave(row, on ? 'false' : 'true')}>
        {on ? 'Yes' : 'No'}
      </Button>
    );
  }
  return <InlineText value={row.value ?? ''} label={row.key} placeholder='Not set' onSave={async (next) => onSave(row, next)} />;
}

function AddProperty({ onAdd }: { onAdd: (key: string, valueType: string) => Promise<string | null> }): ReactElement {
  const keyId = useId();
  const typeId = useId();
  const [key, setKey] = useState('');
  const [valueType, setValueType] = useState('text');
  const [problem, setProblem] = useState<string | null>(null);
  const submit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    const trimmed = key.trim();
    if (trimmed === '') {
      setProblem('Name the property first');
      return;
    }
    const failed = await onAdd(trimmed, valueType);
    setProblem(failed);
    if (failed === null) setKey('');
  };
  return (
    <form onSubmit={(event) => void submit(event)} className='grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-end'>
      <div className='grid min-w-0 gap-1'>
        <label htmlFor={keyId} className='text-sm font-medium'>
          New property
        </label>
        <Input id={keyId} value={key} maxLength={100} onChange={(event) => setKey(event.target.value)} placeholder='Height, population, allegiance…' />
      </div>
      <div className='grid gap-1'>
        <label htmlFor={typeId} className='text-sm font-medium'>
          Kind of value
        </label>
        <select id={typeId} value={valueType} onChange={(event) => setValueType(event.target.value)} className='h-10 rounded-md border border-input bg-background px-3 text-sm'>
          {PROPERTY_VALUE_TYPES.map((type) => (
            <option key={type} value={type}>
              {TYPE_WORDS[type] ?? type}
            </option>
          ))}
        </select>
      </div>
      <Button type='submit'>Add property</Button>
      {problem !== null && (
        <p role='alert' className='text-sm text-destructive sm:col-span-full'>
          {problem}
        </p>
      )}
    </form>
  );
}

export function PropertyList<T extends PropertyRow>({
  rows,
  error,
  onRetry,
  canEdit = false,
  onSave,
  onAdd,
  onRemove,
  problem = null,
}: {
  rows: readonly T[] | undefined;
  error?: Error | undefined;
  onRetry?: () => Promise<unknown>;
  /** Whether the person may change the record's properties (the back end checks again). */
  canEdit?: boolean;
  onSave?: (row: T, value: string) => Promise<string | null>;
  onAdd?: (key: string, valueType: string) => Promise<string | null>;
  onRemove?: (row: T) => void;
  /** Why the last write failed, if it did. */
  problem?: string | null;
}): ReactElement {
  const editable = canEdit && onSave !== undefined;
  return (
    <section aria-labelledby='properties-title' className='space-y-3'>
      <h2 id='properties-title' className='text-lg font-semibold'>
        Properties
      </h2>
      <WriteProblem problem={problem} />
      {error !== undefined && <LoadProblem what='the properties' error={error} onRetry={onRetry} />}
      {rows === undefined && error === undefined && <SkeletonRows rows={3} label='Loading the properties' />}
      {rows !== undefined && rows.length === 0 && <p className='text-sm text-muted-foreground'>No properties yet.</p>}
      {rows !== undefined && rows.length > 0 && (
        <dl aria-label='Properties' className='divide-y rounded-xl border'>
          {rows.map((row) => (
            <div key={row.id} className='grid min-h-12 grid-cols-[minmax(0,2fr)_minmax(0,3fr)_auto] items-center gap-3 px-3 py-2'>
              <dt className='flex min-w-0 items-center gap-2 font-medium'>
                <span className='[overflow-wrap:anywhere]'>{row.key}</span>
                {row.is_private && (
                  <span className='inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground'>
                    <Lock aria-hidden className='size-3' />
                    Private
                  </span>
                )}
              </dt>
              <dd className='min-w-0'>{editable && onSave !== undefined ? <EditValue row={row} onSave={onSave} /> : <Value row={row} />}</dd>
              <dd>
                {canEdit && onRemove !== undefined ? (
                  <Button type='button' size='icon' variant='ghost' aria-label={`Remove property: ${row.key}`} onClick={() => onRemove(row)}>
                    <Trash2 aria-hidden className='size-4' />
                  </Button>
                ) : null}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {canEdit && onAdd !== undefined && <AddProperty onAdd={onAdd} />}
    </section>
  );
}
