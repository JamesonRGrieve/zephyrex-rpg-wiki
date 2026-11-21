// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, within } from 'storybook/test';
import { RelationList } from './RelationList';

const meta: Meta<typeof RelationList> = {
  title: 'World/Relation list',
  component: RelationList,
  args: {
    lines: [
      { id: 'r1', name: "Thieves' Guild", href: '/w/salt/faction/tg', kind: 'rival', intensity: -0.8, colour: '#ff0000', mirrored: false },
      { id: 'r2', name: 'Mira', href: '/w/salt/person/mira', kind: 'serves', intensity: 0.5, colour: null, mirrored: true },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByLabelText('Attitude -80')).toBeInTheDocument();
    await expect(canvas.getByLabelText('Mirrored')).toBeInTheDocument();
  },
};

export const NoRelations: Story = {
  args: { lines: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No relations yet.')).toBeInTheDocument();
  },
};

export const LoadFailed: Story = {
  args: { lines: undefined, error: new Error('The server did not answer'), onRetry: fn(() => Promise.resolve()) },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  },
};
