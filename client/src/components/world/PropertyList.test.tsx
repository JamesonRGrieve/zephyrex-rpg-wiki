// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PropertyList, type PropertyRow } from './PropertyList';

const ROWS: PropertyRow[] = [
  { id: 'p1', key: 'Population', value: '9 billion', value_type: 'text', is_private: false },
  { id: 'p2', key: 'Garrison', value: '3', value_type: 'number', is_private: true },
  { id: 'p3', key: 'Shrine world', value: 'true', value_type: 'boolean', is_private: false },
  { id: 'p4', key: 'Map', value: 'javascript:alert(1)', value_type: 'link', is_private: false },
  { id: 'p5', key: 'Records', value: '/w/1/journal/2', value_type: 'link', is_private: false },
];

describe('PropertyList', () => {
  it('reads each value by its type, marks private ones and follows only safe links', () => {
    render(<PropertyList rows={ROWS} />);
    expect(screen.getByText('9 billion')).toBeInTheDocument();
    expect(screen.getByText('Yes')).toBeInTheDocument();
    expect(screen.getByText('Private')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'javascript:alert(1)' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: '/w/1/journal/2' })).toHaveAttribute('href', '/w/1/journal/2');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('lets an editor flip a yes/no, change a value, remove one and add one', async () => {
    const onSave = vi.fn(async () => null);
    const onAdd = vi.fn(async () => null);
    const onRemove = vi.fn();
    render(<PropertyList rows={ROWS} canEdit onSave={onSave} onAdd={onAdd} onRemove={onRemove} />);
    await userEvent.click(screen.getByRole('button', { name: 'Yes: Shrine world' }));
    expect(onSave).toHaveBeenCalledWith(ROWS[2], 'false');
    await userEvent.click(screen.getByRole('button', { name: 'Remove property: Garrison' }));
    expect(onRemove).toHaveBeenCalledWith(ROWS[1]);
    await userEvent.type(screen.getByLabelText('New property'), 'Tithe grade');
    await userEvent.selectOptions(screen.getByLabelText('Kind of value'), 'text');
    await userEvent.click(screen.getByRole('button', { name: 'Add property' }));
    expect(onAdd).toHaveBeenCalledWith('Tithe grade', 'text');
  });

  it('says a key is needed, and shows the empty, loading, failed and write-problem states', async () => {
    const onAdd = vi.fn(async () => null);
    const { rerender } = render(<PropertyList rows={[]} canEdit onSave={vi.fn()} onAdd={onAdd} />);
    expect(screen.getByText('No properties yet.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Add property' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Name the property first');
    expect(onAdd).not.toHaveBeenCalled();
    rerender(<PropertyList rows={undefined} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    rerender(<PropertyList rows={undefined} error={new Error('offline')} />);
    expect(screen.getByText('offline')).toBeInTheDocument();
    rerender(<PropertyList rows={ROWS} problem='The property could not be saved: offline' />);
    expect(screen.getByRole('alert')).toHaveTextContent('could not be saved');
  });
});
