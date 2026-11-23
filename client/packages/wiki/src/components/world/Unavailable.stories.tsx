// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { Unavailable } from './Unavailable';

const meta: Meta<typeof Unavailable> = { title: 'Wiki/World/Unavailable', component: Unavailable, args: { what: 'people' } };
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('This server doesn’t keep people.')).toBeInTheDocument();
  },
};
