// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { wikiHandlers } from '../testing/wiki.mocks';
import { WorldsPage } from './WorldsPage';

const meta: Meta<typeof WorldsPage> = {
  title: 'Wiki/Pages/Worlds',
  component: WorldsPage,
  parameters: { layout: 'fullscreen', msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** Each setting with its campaigns, and a way into its canon. */
export const OneSetting: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('heading', { level: 1, name: 'Worlds' })).toBeInTheDocument();
    await expect(await canvas.findByRole('heading', { name: 'Reality' })).toBeInTheDocument();
    await expect(await canvas.findByRole('link', { name: /Harbour Lights/ })).toBeInTheDocument();
    await expect(canvas.getByRole('link', { name: 'Its canon: places, people and lore' })).toBeInTheDocument();
  },
};

/** A back end without rpg_core has no campaigns: the page says so instead of failing. */
export const WithoutCampaigns: Story = {
  parameters: { msw: { handlers: wikiHandlers({ extensions: ['genealogy'] }) } },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByRole('heading', { level: 1, name: 'Worlds' })).toBeInTheDocument();
  },
};
