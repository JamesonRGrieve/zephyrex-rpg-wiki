// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { CAMPAIGN_ID, wikiHandlers } from '../testing/wiki.mocks';
import { RecordPage } from './RecordPage';

const meta: Meta<typeof RecordPage> = {
  title: 'Wiki/Pages/Record',
  component: RecordPage,
  args: { world: CAMPAIGN_ID, kind: 'person', id: 'person-1' },
  parameters: { layout: 'fullscreen', msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** A person's page: who they are, where they stand, and their panels. */
export const Person: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Mara Quill' })).toBeInTheDocument();
    await expect(await canvas.findByText('Keeps the Lantern House.')).toBeInTheDocument();
  },
};

/** A hook's page. */
export const Hook: Story = {
  args: { kind: 'hook', id: 'hook-1' },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByRole('heading', { level: 1, name: 'Who lit the lighthouse?' })).toBeInTheDocument();
  },
};

/** A place's page. */
export const Place: Story = {
  args: { kind: 'location', id: 'location-3' },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByRole('heading', { level: 1, name: 'The Lantern House' })).toBeInTheDocument();
  },
};
