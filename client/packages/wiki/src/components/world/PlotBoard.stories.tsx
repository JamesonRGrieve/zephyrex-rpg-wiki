// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { PlotBoard } from './PlotBoard';

const meta: Meta<typeof PlotBoard> = {
  title: 'Wiki/World/Plot board',
  component: PlotBoard,
  args: {
    hooks: [
      { id: 'a', name: 'Arrive at Minoris', href: '/w/s/hook/a', state: 'resolved', excuse: null },
      { id: 'b', name: 'Hear the dock story', href: '/w/s/hook/b', state: 'available', excuse: null },
      { id: 'c', name: 'Hear the vox ghost', href: '/w/s/hook/c', state: 'needs_check', excuse: null },
      { id: 'd', name: 'Geller field repaired', href: '/w/s/hook/d', state: 'blocked', excuse: 'Rech estimates 5 to 7 days for the repairs.' },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Rech estimates 5 to 7 days for the repairs.')).toBeInTheDocument();
  },
};

export const FirstRun: Story = {
  args: { hooks: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No hooks in this campaign yet. Add one from Hooks.')).toBeInTheDocument();
  },
};
