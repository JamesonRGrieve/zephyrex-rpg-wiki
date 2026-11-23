// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { Landing } from './Landing';

const meta: Meta<typeof Landing> = {
  title: 'Wiki/App/Landing',
  component: Landing,
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof Landing>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('heading', { level: 1, name: 'Your world, written down' })).toBeInTheDocument();
    await expect(canvas.getByRole('region', { name: 'What it will do' })).toBeInTheDocument();
    await expect(canvas.getByRole('table')).toBeInTheDocument();
  },
};

/** The landing page at phone width: the header folds into its menu. */
export const Phone: Story = {
  globals: { viewport: { value: 'mobile1' } },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Menu')).toBeInTheDocument();
  },
};
