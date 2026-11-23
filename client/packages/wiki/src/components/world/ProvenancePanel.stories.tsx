// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { ProvenancePanel } from './ProvenancePanel';

const meta: Meta<typeof ProvenancePanel> = {
  title: 'Wiki/World/Provenance panel',
  component: ProvenancePanel,
  args: { provenance: 'official', source: 'Dark Heresy: Purge the Unclean, Fantasy Flight Games, p. 12', onSave: fn(async () => null) },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Official: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Official')).toBeInTheDocument();
  },
};

export const Homebrew: Story = {
  args: { provenance: 'homebrew', source: null, onSave: undefined },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Homebrew')).toBeInTheDocument();
  },
};

export const Editing: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Edit origin' }));
    await userEvent.selectOptions(canvas.getByLabelText('Origin'), 'adapted');
    await userEvent.click(canvas.getByRole('button', { name: 'Save origin' }));
    await expect(args.onSave).toHaveBeenCalledWith({ provenance: 'adapted', source: 'Dark Heresy: Purge the Unclean, Fantasy Flight Games, p. 12' });
  },
};
