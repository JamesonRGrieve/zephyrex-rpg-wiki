// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { voice as filledVoice } from '../../lib/names';
import { VoicePanel } from './VoicePanel';

const meta: Meta<typeof VoicePanel> = {
  title: 'Wiki/World/Voice panel',
  component: VoicePanel,
  args: {
    voice: filledVoice({
      personality: 'Gruff but fair; owes the Circle Compact a favour and hates it.',
      speech: 'Short sentences. Calls everyone "lad".',
      first_message: 'Stalls are full. Unless you’re paying double.',
      examples: ['Holst: No credit, lad.', 'Holst: The shard? Ask the druids.'],
      system_prompt: 'You are Holst, the stablemaster of Brindlemarsh.',
      depth_prompt: { prompt: 'Holst distrusts anyone from the Circle Compact.', depth: 2, role: 'system' },
      talkativeness: 0.3,
    }),
    onSave: fn(async () => null),
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Reading: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Holst: No credit, lad.')).toBeInTheDocument();
    await expect(within(canvasElement).getByText('Depth 2, as system')).toBeInTheDocument();
  },
};

export const Editing: Story = {
  args: { canEdit: true },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Edit voice' }));
    await userEvent.click(canvas.getByRole('button', { name: 'Save voice' }));
    await expect(args.onSave).toHaveBeenCalled();
  },
};

export const Empty: Story = {
  args: { voice: null, canEdit: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No voice yet.')).toBeInTheDocument();
  },
};
