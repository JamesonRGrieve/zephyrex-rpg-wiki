// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { voice } from '../../lib/names';
import { VoicePanel } from './VoicePanel';

const VOICE = voice({ personality: 'Gruff, fair.', speech: 'Short words.', first_message: 'What?', examples: ['Holst: No.', 'Holst: Pay first.'] });

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
    expect(onSave).toHaveBeenCalledWith({ ...voice({}), personality: 'Kind', examples: ['Hello.', 'Goodbye.'] });
    expect(screen.getByRole('alert')).toHaveTextContent('offline');
    await userEvent.click(screen.getByRole('button', { name: 'Save voice' }));
    expect(screen.queryByRole('button', { name: 'Save voice' })).not.toBeInTheDocument();
  });

  it("shows a card's prompts and Character's note, and saves the note with its depth and role", async () => {
    const card = voice({ personality: 'Gruff', system_prompt: 'You are Holst.', depth_prompt: { prompt: 'Distrusts strangers.', depth: 2, role: 'system' }, talkativeness: 0.3 });
    const onSave = vi.fn().mockResolvedValue(null);
    render(<VoicePanel voice={card} canEdit onSave={onSave} />);
    expect(screen.getByText('You are Holst.')).toBeInTheDocument();
    expect(screen.getByText('Depth 2, as system')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Edit voice' }));
    await userEvent.selectOptions(screen.getByLabelText('As'), 'user');
    await userEvent.click(screen.getByLabelText('Across chats'));
    await userEvent.click(screen.getByRole('button', { name: 'Save voice' }));
    expect(onSave).toHaveBeenCalledWith({ ...card, depth_prompt: { prompt: 'Distrusts strangers.', depth: 2, role: 'user' }, across_chats: true });
  });

  it("saves an emptied Character's note as none", async () => {
    const onSave = vi.fn().mockResolvedValue(null);
    render(<VoicePanel voice={voice({ depth_prompt: { prompt: 'Old note.' } })} canEdit onSave={onSave} />);
    await userEvent.click(screen.getByRole('button', { name: 'Edit voice' }));
    await userEvent.clear(screen.getByLabelText("Character's note", { selector: 'textarea' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save voice' }));
    expect(onSave.mock.calls[0]?.[0].depth_prompt).toBeNull();
  });
});
