// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { CAMPAIGN_ID, SETTING_SCOPE, wikiHandlers } from '../testing/wiki.mocks';
import { KindPage } from './KindPage';

const meta: Meta<typeof KindPage> = {
  title: 'Wiki/Pages/Records of a kind',
  component: KindPage,
  args: { world: CAMPAIGN_ID, kind: 'person' },
  parameters: { layout: 'fullscreen', msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** A campaign's people. */
export const People: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'People of Harbour Lights' })).toBeInTheDocument();
    await expect((await canvas.findAllByRole('link', { name: /Mara Quill/ })).length).toBeGreaterThan(0);
  },
};

/** Places, with the tree of where each sits beside the list. */
export const Places: Story = {
  args: { kind: 'location' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Places of Harbour Lights' })).toBeInTheDocument();
    await expect((await canvas.findAllByRole('link', { name: /The Lantern House/ })).length).toBeGreaterThan(0);
  },
};

/** A setting's canon: its records that belong to no campaign. */
export const SettingCanon: Story = {
  args: { world: SETTING_SCOPE, kind: 'location' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Places of Reality' })).toBeInTheDocument();
    await expect((await canvas.findAllByRole('link', { name: /The Old Lighthouse/ })).length).toBeGreaterThan(0);
  },
};
