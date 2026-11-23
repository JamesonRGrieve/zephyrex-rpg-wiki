// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { ElevatePanel } from './ElevatePanel';

const meta: Meta<typeof ElevatePanel> = {
  title: 'Wiki/World/Elevate panel',
  component: ElevatePanel,
  args: { scenario: { name: 'The Rusty Anchor' }, elevated: null, onElevate: fn(async () => null) },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const CampaignOnly: Story = {
  play: async ({ canvasElement, args }) => {
    await userEvent.click(within(canvasElement).getByRole('button', { name: 'Elevate to scenario' }));
    await expect(args.onElevate).toHaveBeenCalledOnce();
  },
};

export const Elevated: Story = {
  args: { elevated: { name: 'Old Tam', href: '/w/s1/person/p2' } },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('link', { name: 'Old Tam' })).toBeInTheDocument();
    await expect(within(canvasElement).queryByRole('button')).not.toBeInTheDocument();
  },
};
