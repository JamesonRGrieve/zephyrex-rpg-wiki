// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { CAMPAIGN_ID, SETTING_SCOPE, wikiHandlers } from '../../testing/wiki.mocks';
import { WorldNav } from './WorldNav';

const meta: Meta<typeof WorldNav> = {
  title: 'Wiki/World/World navigation',
  component: WorldNav,
  args: { world: CAMPAIGN_ID, current: 'person' },
  parameters: { msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** A campaign's pages: About, each kind, the taxonomy and the plot board; the current one marked. */
export const Campaign: Story = {
  play: async ({ canvasElement }) => {
    const nav = within(within(canvasElement).getByRole('navigation', { name: 'This campaign' }));
    await expect(nav.getByRole('link', { name: 'About' })).toBeInTheDocument();
    await expect(await nav.findByRole('link', { name: 'Plot board' })).toBeInTheDocument();
    await expect(nav.getByRole('link', { name: 'People' })).toHaveAttribute('aria-current', 'page');
  },
};

/** A setting's canon has no About page and no plot board (its campaigns have them). */
export const Setting: Story = {
  args: { world: SETTING_SCOPE, current: 'location' },
  play: async ({ canvasElement }) => {
    const nav = within(within(canvasElement).getByRole('navigation', { name: 'This setting' }));
    await expect(await nav.findByRole('link', { name: 'Taxonomy' })).toBeInTheDocument();
    await expect(nav.queryByRole('link', { name: 'Plot board' })).not.toBeInTheDocument();
    await expect(nav.queryByRole('link', { name: 'About' })).not.toBeInTheDocument();
  },
};

/** Without world_taxonomy and world_narrative, their links aren't shown. */
export const FewerExtensions: Story = {
  parameters: { msw: { handlers: wikiHandlers({ extensions: ['rpg_core', 'genealogy', 'world_spatial'] }) } },
  play: async ({ canvasElement }) => {
    const nav = within(within(canvasElement).getByRole('navigation', { name: 'This campaign' }));
    await expect(nav.getByRole('link', { name: 'All settings' })).toBeInTheDocument();
    await expect(nav.queryByRole('link', { name: 'Taxonomy' })).not.toBeInTheDocument();
  },
};
