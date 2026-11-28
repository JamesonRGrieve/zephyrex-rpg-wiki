// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { InvariantsPanel } from './InvariantsPanel';

const meta: Meta<typeof InvariantsPanel> = {
  title: 'Wiki/World/Invariants panel',
  component: InvariantsPanel,
  args: {
    invariants: ['Never turns away a lame horse', 'Never sells to the Circle Compact on credit, whatever they offer and however long they have been coming to the stable'],
    onSave: fn(async () => null),
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Reading: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText('Never turns away a lame horse')).toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: 'Edit lines' })).toBeNull();
  },
};

export const Editing: Story = {
  args: { canEdit: true },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Edit lines' }));
    const box = canvas.getByLabelText('Lines they never cross');
    await userEvent.type(box, '\n  \nNever breaks a sworn oath ');
    await userEvent.click(canvas.getByRole('button', { name: 'Save lines' }));
    await expect(args.onSave).toHaveBeenCalledWith([
      'Never turns away a lame horse',
      'Never sells to the Circle Compact on credit, whatever they offer and however long they have been coming to the stable',
      'Never breaks a sworn oath',
    ]);
    await expect(canvas.getByRole('button', { name: 'Edit lines' })).toBeInTheDocument();
  },
};

export const Refused: Story = {
  args: { canEdit: true, onSave: fn(async () => 'At most 12 invariants of at most 200 characters') },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Edit lines' }));
    await userEvent.click(canvas.getByRole('button', { name: 'Save lines' }));
    await expect(canvas.getByRole('alert')).toHaveTextContent('At most 12 invariants');
  },
};

export const Empty: Story = {
  args: { invariants: [], canEdit: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No lines yet.')).toBeInTheDocument();
  },
};
