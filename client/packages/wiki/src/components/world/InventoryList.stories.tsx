// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, within } from 'storybook/test';
import { InventoryList } from './InventoryList';

const meta: Meta<typeof InventoryList> = {
  title: 'Wiki/World/Inventory list',
  component: InventoryList,
  args: {
    lines: [
      { id: 'c1', name: 'Brine bar', href: '/w/w1/item/i2', quantity: 50 },
      { id: 'c2', name: 'Salt-steel sabre', href: '/w/w1/item/i1', quantity: 1 },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('link', { name: 'Brine bar' })).toBeInTheDocument();
    await expect(canvas.getByText('× 50')).toBeInTheDocument();
  },
};

export const NothingCarried: Story = {
  args: { lines: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Nothing carried.')).toBeInTheDocument();
  },
};

export const LoadFailed: Story = {
  args: { lines: undefined, error: new Error('The server did not answer'), onRetry: fn(() => Promise.resolve()) },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  },
};
