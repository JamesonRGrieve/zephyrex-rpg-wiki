// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { FACTIONS, PLACES } from './fixtures';
import { ParentTree } from './ParentTree';

const meta: Meta<typeof ParentTree<(typeof PLACES)[number] | (typeof FACTIONS)[number]>> = {
  title: 'World/Parent tree',
  component: ParentTree,
  args: { rows: PLACES, label: 'Places by where they sit', hrefOf: (row) => `/w/w1/location/${row.id}` },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('link', { name: /The Gull/ })).toHaveAttribute('href', '/w/w1/location/l3');
  },
};

export const Organisations: Story = {
  args: { rows: FACTIONS, label: 'Organisations by who they answer to', hrefOf: (row) => `/w/w1/faction/${row.id}` },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('link', { name: /The Cadet Line/ })).toHaveAttribute('href', '/w/w1/faction/f2');
  },
};
