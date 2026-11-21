// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PlayStyles } from './PlayStyles';

const OPTIONS = [
  { id: 't1', name: 'mystery' },
  { id: 't2', name: 'combat-heavy' },
  { id: 't3', name: 'horror' },
];

describe('PlayStyles', () => {
  it('shows the chips, read only for a reader', () => {
    render(<PlayStyles styles={[{ id: 'l1', name: 'mystery' }]} options={OPTIONS} />);
    expect(screen.getByText('mystery')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Remove mystery' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Add a play style')).not.toBeInTheDocument();
  });

  it('adds a shared one not yet on, makes a new one, and takes one off', async () => {
    const onAdd = vi.fn();
    const onCreate = vi.fn();
    const onRemove = vi.fn();
    render(<PlayStyles styles={[{ id: 'l1', name: 'mystery' }]} options={OPTIONS} onAdd={onAdd} onCreate={onCreate} onRemove={onRemove} />);
    expect(screen.queryByRole('option', { name: 'mystery' })).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Add a play style'), 'horror');
    await userEvent.click(screen.getByRole('button', { name: 'Add' }));
    expect(onAdd).toHaveBeenCalledWith('t3');
    await userEvent.type(screen.getByLabelText('Or a new one'), ' slow-burn ');
    await userEvent.click(screen.getByRole('button', { name: 'Make it' }));
    expect(onCreate).toHaveBeenCalledWith('slow-burn');
    await userEvent.click(screen.getByRole('button', { name: 'Remove mystery' }));
    expect(onRemove).toHaveBeenCalledWith({ id: 'l1', name: 'mystery' });
  });
});
