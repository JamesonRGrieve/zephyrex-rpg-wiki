// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ProvenancePanel } from './ProvenancePanel';

describe('ProvenancePanel', () => {
  it('reads a record stored before provenance as homebrew, and offers no edit to a reader', () => {
    render(<ProvenancePanel provenance={null} source={null} />);
    expect(screen.getByText('Homebrew')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit origin' })).not.toBeInTheDocument();
  });

  it('shows an official source, and saves a change with its source trimmed', async () => {
    const onSave = vi.fn().mockResolvedValue(null);
    render(<ProvenancePanel provenance='official' source='Purge the Unclean, FFG' onSave={onSave} />);
    expect(screen.getByText('Purge the Unclean, FFG')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Edit origin' }));
    await userEvent.selectOptions(screen.getByLabelText('Origin'), 'adapted');
    await userEvent.clear(screen.getByLabelText('Source'));
    await userEvent.type(screen.getByLabelText('Source'), '  Purge the Unclean, p. 12 ');
    await userEvent.click(screen.getByRole('button', { name: 'Save origin' }));
    expect(onSave).toHaveBeenCalledWith({ provenance: 'adapted', source: 'Purge the Unclean, p. 12' });
    expect(screen.queryByRole('button', { name: 'Save origin' })).not.toBeInTheDocument();
  });

  it('sends no source for homebrew, and keeps the form with the reason when saving fails', async () => {
    const onSave = vi.fn().mockResolvedValue('The origin could not be saved: offline');
    render(<ProvenancePanel provenance='official' source='A book' onSave={onSave} />);
    await userEvent.click(screen.getByRole('button', { name: 'Edit origin' }));
    await userEvent.selectOptions(screen.getByLabelText('Origin'), 'homebrew');
    expect(screen.getByLabelText('Source')).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Save origin' }));
    expect(onSave).toHaveBeenCalledWith({ provenance: 'homebrew', source: null });
    expect(screen.getByRole('alert')).toHaveTextContent('offline');
  });
});
