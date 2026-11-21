// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DispositionList } from './DispositionList';

describe('DispositionList', () => {
  it('shows each target with its current attitude, its band for a nuance, and what changed it', () => {
    render(
      <DispositionList
        lines={[
          { key: 'party', target: 'The party', href: null, attitude: 'wary', because: 'Hear the dock story', note: 'She knows what they’re circling' },
          { key: 'p1', target: 'Captain Ross', href: '/w/s/person/p1', attitude: 'guarded', because: null, note: null },
        ]}
      />,
    );
    const rows = within(screen.getByRole('list', { name: 'Dispositions' })).getAllByRole('listitem');
    expect(rows[0]).toHaveTextContent('Since Hear the dock story');
    expect(within(rows[1]!).getByRole('link', { name: 'Captain Ross' })).toHaveAttribute('href', '/w/s/person/p1');
    expect(rows[1]).toHaveTextContent('guarded (cautious-neutral)');
    expect(rows[1]).toHaveTextContent('Baseline');
  });

  it('shows loading, a failure with a retry, and none', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<DispositionList lines={undefined} />);
    expect(screen.getByText('Loading the dispositions')).toBeInTheDocument();
    rerender(<DispositionList lines={undefined} error={new Error('offline')} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
    rerender(<DispositionList lines={[]} />);
    expect(screen.getByText('No dispositions yet.')).toBeInTheDocument();
  });
});
