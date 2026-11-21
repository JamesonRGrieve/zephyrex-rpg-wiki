// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { attitudeOf, RelationList } from './RelationList';

describe('attitudeOf', () => {
  it('shows -1 to +1 as a signed -100 to +100', () => {
    expect([attitudeOf(-0.8), attitudeOf(0), attitudeOf(0.5), attitudeOf(null)]).toEqual(['-80', '0', '+50', null]);
  });
});

describe('RelationList', () => {
  it('lists each tie with its kind, linked end, attitude and mirror', () => {
    render(
      <RelationList
        lines={[{ id: 'r1', name: "Thieves' Guild", href: '/w/salt/faction/tg', kind: 'rival', intensity: -0.8, colour: '#ff0000', mirrored: true }]}
      />,
    );
    const row = within(screen.getByRole('list', { name: 'Relations' })).getByRole('listitem');
    expect(within(row).getByRole('link', { name: "Thieves' Guild" })).toHaveAttribute('href', '/w/salt/faction/tg');
    expect(within(row).getByLabelText('Attitude -80')).toBeInTheDocument();
    expect(within(row).getByLabelText('Mirrored')).toBeInTheDocument();
  });

  it('shows loading, a load failure with a retry, and none', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<RelationList lines={undefined} />);
    expect(screen.getByText('Loading the relations')).toBeInTheDocument();
    rerender(<RelationList lines={undefined} error={new Error('offline')} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
    rerender(<RelationList lines={[]} />);
    expect(screen.getByText('No relations yet.')).toBeInTheDocument();
  });
});
