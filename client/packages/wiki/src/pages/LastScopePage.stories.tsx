// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { LastScopePage } from './LastScopePage';

const meta: Meta<typeof LastScopePage> = {
  title: 'Wiki/Pages/Last setting or campaign',
  component: LastScopePage,
  args: { kind: 'person' },
  parameters: { layout: 'fullscreen' },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** While it sends the person on to the page they were last on, it shows that it is opening. */
export const Opening: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Opening')).toBeInTheDocument();
  },
};
