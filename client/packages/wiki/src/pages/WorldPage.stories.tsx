// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { CAMPAIGN_ID, wikiHandlers } from '../testing/wiki.mocks';
import { WorldPage } from './WorldPage';

const meta: Meta<typeof WorldPage> = {
  title: 'Wiki/Pages/Campaign',
  component: WorldPage,
  args: { world: CAMPAIGN_ID },
  parameters: { layout: 'fullscreen', msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** A campaign's own page: its name, description and origin, and its pages. */
export const About: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Harbour Lights' })).toBeInTheDocument();
    await expect(await canvas.findByText('A small port town and the storm that cut it off.')).toBeInTheDocument();
    await expect(canvas.getByRole('navigation', { name: 'This campaign' })).toBeInTheDocument();
  },
};
