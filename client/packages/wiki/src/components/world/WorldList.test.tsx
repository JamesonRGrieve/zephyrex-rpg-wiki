// SPDX-License-Identifier: AGPL-3.0-or-later
import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { UNDO_MS } from 'zephyrex/hooks/useToast';
import { WORLDS } from './fixtures';
import { WorldList } from './WorldList';

const noop = () => Promise.resolve(true);

describe('WorldList', () => {
  it('lists the worlds, each opening its places', () => {
    render(<WorldList worlds={WORLDS} onCreate={noop} onDelete={vi.fn()} />);
    expect(screen.getByRole('link', { name: /The Salt Coast/ })).toHaveAttribute('href', '/w/w1/location');
  });

  it('shows loading, a load failure with a retry, and a first world to make', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<WorldList worlds={undefined} onCreate={noop} onDelete={vi.fn()} />);
    expect(screen.getByText('Loading your worlds')).toBeInTheDocument();
    rerender(<WorldList worlds={undefined} error={new Error('offline')} onRetry={onRetry} onCreate={noop} onDelete={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
    rerender(<WorldList worlds={[]} onCreate={noop} onDelete={vi.fn()} />);
    expect(screen.getByText(/No worlds yet/)).toBeInTheDocument();
  });

  it('makes a world from its name and clears the field once it lands', async () => {
    const onCreate = vi.fn().mockResolvedValue(true);
    render(<WorldList worlds={[]} onCreate={onCreate} onDelete={vi.fn()} />);
    const field = screen.getByLabelText('New world');
    await userEvent.type(field, '  Hollowmere ');
    await userEvent.click(screen.getByRole('button', { name: 'Make it' }));
    expect(onCreate).toHaveBeenCalledWith('Hollowmere');
    expect(field).toHaveValue('');
  });

  it('deletes only once the undo window has passed, and never flashes the first-run state', () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const onDelete = vi.fn();
      render(<WorldList worlds={[WORLDS[0]!]} onCreate={noop} onDelete={onDelete} />);
      fireEvent.click(screen.getByRole('button', { name: 'Delete The Salt Coast' }));
      expect(screen.queryByRole('link', { name: /The Salt Coast/ })).not.toBeInTheDocument();
      expect(screen.queryByText(/No worlds yet/)).not.toBeInTheDocument();
      expect(onDelete).not.toHaveBeenCalled();
      act(() => {
        vi.advanceTimersByTime(UNDO_MS);
      });
      expect(onDelete).toHaveBeenCalledWith(WORLDS[0]);
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows why a write failed', () => {
    render(<WorldList worlds={WORLDS} onCreate={noop} onDelete={vi.fn()} problem='The world could not be made: offline' />);
    expect(screen.getByRole('alert')).toHaveTextContent('offline');
  });
});
