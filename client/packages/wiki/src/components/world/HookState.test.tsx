// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { HookState } from './HookState';

const base = { needs: 'Arrive', excuse: 'Renn won’t talk to strangers', resolvedOn: null, onResolve: vi.fn(), onUnresolve: vi.fn() };

describe('HookState', () => {
  it('shows a blocked hook with what it needs and the GM’s excuse, and marks it as happened', async () => {
    const onResolve = vi.fn();
    render(<HookState {...base} state='blocked' onResolve={onResolve} />);
    expect(screen.getByText('Blocked')).toBeInTheDocument();
    expect(screen.getByText('Arrive')).toBeInTheDocument();
    expect(screen.getByText('Renn won’t talk to strangers')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Mark as happened' }));
    expect(onResolve).toHaveBeenCalled();
  });

  it('keeps the excuse for blocked hooks only, and undoes a resolution', async () => {
    const onUnresolve = vi.fn();
    render(<HookState {...base} state='resolved' resolvedOn='21 Nov 2026' onUnresolve={onUnresolve} />);
    expect(screen.queryByText('Renn won’t talk to strangers')).not.toBeInTheDocument();
    expect(screen.getByText('21 Nov 2026')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Mark as not happened' }));
    expect(onUnresolve).toHaveBeenCalled();
  });

  it('says why a write failed, and waits while one is under way', () => {
    render(<HookState {...base} state='needs_check' busy problem='The hook could not be saved: offline' />);
    expect(screen.getByText('Needs a check at the table')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('offline');
    expect(screen.getByRole('button', { name: 'Mark as happened' })).toBeDisabled();
  });
});
