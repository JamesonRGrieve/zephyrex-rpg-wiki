// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { VoicePanel } from './VoicePanel';

const VOICE = { personality: 'Gruff, fair.', speech: 'Short words.', first_message: 'What?', examples: ['Holst: No.', 'Holst: Pay first.'] };

describe('VoicePanel', () => {
  it('shows each part it has, and says it is for the GM', () => {
    render(<VoicePanel voice={VOICE} />);
    expect(screen.getByText('Gruff, fair.')).toBeInTheDocument();
    expect(screen.getByText('Holst: Pay first.')).toBeInTheDocument();
    expect(screen.getByText(/never shown to players/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit voice' })).not.toBeInTheDocument();
  });

  it('edits the voice, splitting examples at blank lines, and keeps the form open with the reason when saving fails', async () => {
    const onSave = vi.fn().mockResolvedValueOnce('The voice could not be saved: offline').mockResolvedValueOnce(null);
    render(<VoicePanel voice={null} canEdit onSave={onSave} />);
    expect(screen.getByText('No voice yet.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Edit voice' }));
    await userEvent.type(screen.getByLabelText('Personality'), 'Kind');
    await userEvent.type(screen.getByLabelText('Example lines'), 'Hello.{enter}{enter}Goodbye.');
    await userEvent.click(screen.getByRole('button', { name: 'Save voice' }));
    expect(onSave).toHaveBeenCalledWith({ personality: 'Kind', speech: '', first_message: '', examples: ['Hello.', 'Goodbye.'] });
    expect(screen.getByRole('alert')).toHaveTextContent('offline');
    await userEvent.click(screen.getByRole('button', { name: 'Save voice' }));
    expect(screen.queryByRole('button', { name: 'Save voice' })).not.toBeInTheDocument();
  });
});
