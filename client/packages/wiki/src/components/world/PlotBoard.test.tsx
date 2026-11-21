// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { type BoardHook, PlotBoard } from './PlotBoard';

const hook = (id: string, name: string, state: BoardHook['state'], excuse: string | null = null): BoardHook => ({ id, name, href: `/w/s/hook/${id}`, state, excuse });
const HOOKS = [hook('a', 'Arrive', 'resolved'), hook('b', 'Hear the story', 'available'), hook('c', 'Hear the ghost', 'needs_check'), hook('d', 'Repair the Geller field', 'blocked', 'Rech needs a week')];

describe('PlotBoard', () => {
  it('groups hooks by where they stand, with the excuse on blocked ones', () => {
    render(<PlotBoard hooks={HOOKS} />);
    expect(within(screen.getByRole('list', { name: 'Can happen now' })).getByRole('link', { name: 'Hear the story' })).toHaveAttribute('href', '/w/s/hook/b');
    expect(within(screen.getByRole('list', { name: 'Blocked' })).getByText('Rech needs a week')).toBeInTheDocument();
    expect(within(screen.getByRole('list', { name: 'Happened' })).getByText('Arrive')).toBeInTheDocument();
  });

  it('says what to do with no hooks, and shows loading and a failure with a retry', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<PlotBoard hooks={[]} />);
    expect(screen.getByText('No hooks in this campaign yet. Add one from Hooks.')).toBeInTheDocument();
    rerender(<PlotBoard hooks={undefined} />);
    expect(screen.getByText('Loading the plot board')).toBeInTheDocument();
    rerender(<PlotBoard hooks={undefined} error={new Error('offline')} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
  });
});
