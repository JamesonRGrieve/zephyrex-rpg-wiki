// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { WORLDS } from './fixtures';
import { WorldList } from './WorldList';

const meta: Meta<typeof WorldList> = {
  title: 'World/Campaign list',
  component: WorldList,
  args: { worlds: WORLDS, onCreate: fn(() => Promise.resolve(true)), onDelete: fn() },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('list', { name: 'Campaigns' })).toBeInTheDocument();
    // An official world says so; a homebrew one carries no badge.
    await expect(canvas.getByText('official')).toBeInTheDocument();
    await userEvent.type(canvas.getByLabelText('New campaign'), 'Hollowmere');
    await userEvent.click(canvas.getByRole('button', { name: 'Make it' }));
    await expect(args.onCreate).toHaveBeenCalledWith('Hollowmere');
  },
};

export const Loading: Story = {
  args: { worlds: undefined },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Loading the campaigns')).toBeInTheDocument();
  },
};

export const LoadFailed: Story = {
  args: { worlds: undefined, error: new Error('The server did not answer'), onRetry: fn(() => Promise.resolve()) },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  },
};

export const FirstRun: Story = {
  args: { worlds: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText(/No campaigns yet/)).toBeInTheDocument();
  },
};
