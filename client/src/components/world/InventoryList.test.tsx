// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { InventoryList } from './InventoryList';

describe('InventoryList', () => {
  it('lists each carried item with how many, linking the ones it can name', () => {
    render(
      <InventoryList
        lines={[
          { id: 'c1', name: 'Brine bar', href: '/w/w1/item/i2', quantity: 50 },
          { id: 'c2', name: null, href: null, quantity: 1 },
        ]}
      />,
    );
    expect(screen.getByRole('link', { name: 'Brine bar' })).toHaveAttribute('href', '/w/w1/item/i2');
    expect(screen.getByText('× 50')).toBeInTheDocument();
    expect(screen.getByText('An item')).toBeInTheDocument();
  });

  it('shows loading, a load failure with a retry, and nothing carried', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<InventoryList lines={undefined} />);
    expect(screen.getByText('Loading what this carries')).toBeInTheDocument();
    rerender(<InventoryList lines={undefined} error={new Error('offline')} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
    rerender(<InventoryList lines={[]} />);
    expect(screen.getByText('Nothing carried.')).toBeInTheDocument();
  });
});
