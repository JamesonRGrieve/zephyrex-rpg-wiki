// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { HookLinks } from './HookLinks';

const hook = (id: string, name: string) => ({ id, name, href: `/w/salt/hook/${id}` });

describe('HookLinks', () => {
  it('lists what the hook waits on, what it leads to, and who is on it', () => {
    render(
      <HookLinks
        waitsOn={[hook('find', 'Find the map')]}
        leadsTo={[hook('slay', 'Slay the wyrm')]}
        takers={[{ id: 'p1', name: 'Hunter Brin', href: '/w/salt/person/brin', status: 'active', progress: 3 }]}
      />,
    );
    expect(within(screen.getByRole('list', { name: 'Waits on' })).getByRole('link', { name: 'Find the map' })).toHaveAttribute(
      'href',
      '/w/salt/hook/find',
    );
    expect(within(screen.getByRole('list', { name: 'Leads to' })).getByText('Slay the wyrm')).toBeInTheDocument();
    expect(within(screen.getByRole('list', { name: 'Who’s on it' })).getByText('active · 3')).toBeInTheDocument();
  });

  it('says so when nothing is linked', () => {
    render(<HookLinks waitsOn={[]} leadsTo={[]} takers={[]} />);
    expect(screen.getByText('Nothing: it can start now.')).toBeInTheDocument();
    expect(screen.getByText('No one yet.')).toBeInTheDocument();
  });

  it('shows loading, then a load failure with a retry', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<HookLinks waitsOn={undefined} leadsTo={[]} takers={[]} />);
    expect(screen.getByText('Loading this hook’s links')).toBeInTheDocument();
    rerender(<HookLinks waitsOn={undefined} leadsTo={undefined} takers={undefined} error={new Error('offline')} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
  });
});
