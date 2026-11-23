// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, userEvent, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { worlds } from '../../features/data/records';
import { CAMPAIGN_ID, wikiHandlers } from '../../testing/wiki.mocks';
import { OriginOf } from './OriginOf';

const meta: Meta = {
  title: 'Wiki/World/Origin of a record',
  component: OriginOf,
  // Rendered, not args: the component is generic in its resource's row, which args would widen.
  render: () => <OriginOf resource={worlds} id={CAMPAIGN_ID} />,
  parameters: { msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** The campaign's origin, read from the server and saved back through it. */
export const SavedThroughItsResource: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole('button', { name: 'Edit origin' }));
    await userEvent.selectOptions(canvas.getByLabelText('Origin'), 'adapted');
    await userEvent.click(canvas.getByRole('button', { name: 'Save origin' }));
    await expect(await canvas.findByText('Adapted')).toBeInTheDocument();
  },
};
