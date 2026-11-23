// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { CAMPAIGN_ID, wikiHandlers } from '../testing/wiki.mocks';
import { PlotPage } from './PlotPage';

const meta: Meta<typeof PlotPage> = {
  title: 'Wiki/Pages/Plot board',
  component: PlotPage,
  args: { world: CAMPAIGN_ID },
  parameters: { layout: 'fullscreen', msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** A campaign's hooks by state: what can happen now, and what waits on what. */
export const Hooks: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Plot board of Harbour Lights' })).toBeInTheDocument();
    await expect((await canvas.findAllByText('Reach the lighthouse')).length).toBeGreaterThan(0);
  },
};
