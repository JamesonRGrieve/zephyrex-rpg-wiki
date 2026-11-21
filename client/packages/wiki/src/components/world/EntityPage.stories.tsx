// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { EntityPage } from './EntityPage';
import { ENTRY } from './fixtures';

const meta: Meta<typeof EntityPage> = {
  title: 'World/Entity page',
  component: EntityPage,
  args: { kind: 'city', entry: ENTRY, description: null, where: { label: 'In', name: 'The Coast', href: '/w/w1/location/l1' } },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText('Founded by smugglers.')).toBeInTheDocument();
    await expect(canvas.getByRole('link', { name: 'The Coast' })).toBeInTheDocument();
  },
};

export const NothingWritten: Story = {
  args: { entry: null, description: null, where: undefined },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Nothing written here yet.')).toBeInTheDocument();
  },
};
