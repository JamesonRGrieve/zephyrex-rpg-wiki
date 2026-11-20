// SPDX-License-Identifier: AGPL-3.0-or-later
import { AlertCircle } from 'lucide-react';
import type { ReactElement } from 'react';

/**
 * Why a write did not land, said where the person is looking (standards page UX and UI): the
 * server's reason, announced as an alert. Nothing when there is none.
 */
export function WriteProblem({ problem }: { problem: string | null }): ReactElement | null {
  if (problem === null) return null;
  return (
    <p
      role='alert'
      className='flex items-start gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive'
    >
      <AlertCircle className='mt-0.5 size-4 shrink-0' aria-hidden />
      <span className='[overflow-wrap:anywhere]'>{problem}</span>
    </p>
  );
}
