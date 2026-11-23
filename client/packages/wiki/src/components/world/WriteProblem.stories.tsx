// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { WriteProblem } from './WriteProblem';

const meta: Meta<typeof WriteProblem> = {
  title: 'Wiki/World/Write problem',
  component: WriteProblem,
  args: { problem: 'The place could not be saved: A location can’t sit under itself or its own descendants' },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('alert')).toHaveTextContent('its own descendants');
  },
};
