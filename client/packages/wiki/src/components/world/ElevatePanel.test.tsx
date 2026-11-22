// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ElevatePanel } from './ElevatePanel';

describe('ElevatePanel', () => {
  it('elevates a campaign-only person and says why it failed', async () => {
    const onElevate = vi.fn().mockResolvedValueOnce('Only the scenario’s GM elevates its people');
    render(<ElevatePanel scenario={{ name: 'The Rusty Anchor' }} elevated={null} onElevate={onElevate} />);
    await userEvent.click(screen.getByRole('button', { name: 'Elevate to scenario' }));
    expect(onElevate).toHaveBeenCalledOnce();
    expect(await screen.findByRole('alert')).toHaveTextContent('Only the scenario’s GM');
  });

  it('links an elevated person to their copy in the scenario', () => {
    render(<ElevatePanel scenario={{ name: 'The Rusty Anchor' }} elevated={{ name: 'Old Tam', href: '/w/s1/person/p2' }} onElevate={vi.fn()} />);
    expect(screen.getByRole('link', { name: 'Old Tam' })).toHaveAttribute('href', '/w/s1/person/p2');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
