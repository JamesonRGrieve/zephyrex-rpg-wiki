// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { DispositionList } from './DispositionList';

const meta: Meta<typeof DispositionList> = {
  title: 'Wiki/World/Disposition list',
  component: DispositionList,
  args: {
    lines: [
      { key: 'party', target: 'The party', href: null, attitude: 'wary', because: 'Dock operative watches the disembark', note: 'Cooperation continues, but it is calibrated.' },
      { key: 'p1', target: 'Cyril', href: '/w/s/person/p1', attitude: 'confiding', because: null, note: null },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Since Dock operative watches the disembark')).toBeInTheDocument();
  },
};

export const NoDispositions: Story = {
  args: { lines: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No dispositions yet.')).toBeInTheDocument();
  },
};
