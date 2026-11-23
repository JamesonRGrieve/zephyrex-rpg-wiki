// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { ScenarioPanel } from './ScenarioPanel';

const meta: Meta<typeof ScenarioPanel> = {
  title: 'Wiki/World/Scenario panel',
  component: ScenarioPanel,
  args: { isScenario: true, onStart: fn(async () => null) },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Scenario: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Start a playthrough' }));
    await expect(args.onStart).toHaveBeenCalledWith(null);
  },
};

export const Playthrough: Story = {
  args: { isScenario: false, scenario: { name: 'The Flicker', href: '/w/s1/about' }, onStart: undefined },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('link', { name: 'The Flicker' })).toBeInTheDocument();
  },
};
