// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { PlayStyles } from './PlayStyles';

const meta: Meta<typeof PlayStyles> = {
  title: 'World/Play styles',
  component: PlayStyles,
  args: {
    styles: [
      { id: 'l1', name: 'mystery' },
      { id: 'l2', name: 'combat-heavy' },
    ],
    options: [
      { id: 't1', name: 'mystery' },
      { id: 't2', name: 'combat-heavy' },
      { id: 't3', name: 'narrative' },
      { id: 't4', name: 'horror' },
    ],
    onAdd: fn(),
    onCreate: fn(),
    onRemove: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Editing: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.selectOptions(canvas.getByLabelText('Add a play style'), 'narrative');
    await userEvent.click(canvas.getByRole('button', { name: 'Add' }));
    await expect(args.onAdd).toHaveBeenCalledWith('t3');
  },
};

export const Reading: Story = {
  args: { onAdd: undefined, onCreate: undefined, onRemove: undefined },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('combat-heavy')).toBeInTheDocument();
  },
};

export const None: Story = {
  args: { styles: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No play style yet.')).toBeInTheDocument();
  },
};
