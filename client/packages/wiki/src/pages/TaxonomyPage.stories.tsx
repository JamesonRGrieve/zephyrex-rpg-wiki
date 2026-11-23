// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { CAMPAIGN_ID, wikiHandlers } from '../testing/wiki.mocks';
import { TaxonomyPage } from './TaxonomyPage';

const meta: Meta<typeof TaxonomyPage> = {
  title: 'Wiki/Pages/Taxonomy',
  component: TaxonomyPage,
  args: { world: CAMPAIGN_ID },
  parameters: { layout: 'fullscreen', msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** A campaign's tags and categories. */
export const Tags: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Taxonomy of Harbour Lights' })).toBeInTheDocument();
    await expect((await canvas.findAllByText('Coastal')).length).toBeGreaterThan(0);
  },
};
