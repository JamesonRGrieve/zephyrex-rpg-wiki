// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { HookState } from './HookState';

const meta: Meta<typeof HookState> = {
  title: 'World/Hook state',
  component: HookState,
  args: {
    state: 'blocked',
    needs: 'Arrive and (a check: skill psyniscience or forbidden-lore or Discover the null)',
    excuse: 'Only a psyker or a scholar hears the ghost on the vox.',
    resolvedOn: null,
    onResolve: fn(),
    onUnresolve: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Blocked: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText('Only a psyker or a scholar hears the ghost on the vox.')).toBeInTheDocument();
    await userEvent.click(canvas.getByRole('button', { name: 'Mark as happened' }));
    await expect(args.onResolve).toHaveBeenCalled();
  },
};

export const NeedsCheck: Story = {
  args: { state: 'needs_check' },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Needs a check at the table')).toBeInTheDocument();
  },
};

export const Resolved: Story = {
  args: { state: 'resolved', resolvedOn: '21 Nov 2026' },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('button', { name: 'Mark as not happened' })).toBeInTheDocument();
  },
};

export const WriteFailed: Story = {
  args: { problem: 'The hook could not be saved: Someone else changed it' },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('alert')).toHaveTextContent('Someone else changed it');
  },
};
