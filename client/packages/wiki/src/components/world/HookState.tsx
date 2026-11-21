// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Where a hook stands (W57, from dh-campaign's tracker): resolved, available, blocked (with the GM's
 * excuse) or waiting on a check at the table, what it needs in words, and the one write here:
 * mark it as happened, or not.
 */
import { CircleCheck, CircleDot, Dices, Lock } from 'lucide-react';
import type { ReactElement } from 'react';
import { Button } from 'zephyrex/ui/button';
import type { HookState as State } from '../../lib/requirements';
import { WriteProblem } from './WriteProblem';

const SAID: Record<State, { label: string; Icon: typeof Lock }> = {
  resolved: { label: 'Happened', Icon: CircleCheck },
  available: { label: 'Can happen now', Icon: CircleDot },
  needs_check: { label: 'Needs a check at the table', Icon: Dices },
  blocked: { label: 'Blocked', Icon: Lock },
};

export interface HookStateProps {
  state: State;
  /** What it needs, in words; null when it needs nothing. */
  needs: string | null;
  excuse: string | null;
  /** When it happened, already formatted; null when it hasn't. */
  resolvedOn: string | null;
  busy?: boolean;
  problem?: string | null;
  onResolve: () => void;
  onUnresolve: () => void;
}

export function HookState({ state, needs, excuse, resolvedOn, busy = false, problem = null, onResolve, onUnresolve }: HookStateProps): ReactElement {
  const { label, Icon } = SAID[state];
  return (
    <section aria-labelledby='hook-state-title' className='space-y-3'>
      <h2 id='hook-state-title' className='text-lg font-semibold'>
        Where it stands
      </h2>
      <p className='flex items-center gap-2 font-medium'>
        <Icon className='size-5 text-muted-foreground' aria-hidden />
        {label}
        {resolvedOn !== null && <span className='text-sm font-normal text-muted-foreground'>{resolvedOn}</span>}
      </p>
      {needs !== null && (
        <p className='text-sm'>
          <span className='text-muted-foreground'>Needs: </span>
          {needs}
        </p>
      )}
      {state === 'blocked' && excuse !== null && <p className='border-l-2 pl-3 text-sm text-muted-foreground'>{excuse}</p>}
      <WriteProblem problem={problem} />
      {state === 'resolved' ? (
        <Button variant='outline' className='min-h-11' disabled={busy} onClick={onUnresolve}>
          Mark as not happened
        </Button>
      ) : (
        <Button className='min-h-11' disabled={busy} onClick={onResolve}>
          Mark as happened
        </Button>
      )}
    </section>
  );
}
