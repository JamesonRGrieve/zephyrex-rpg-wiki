// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, userEvent, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { people } from '../../features/data/records';
import { wikiHandlers } from '../../testing/wiki.mocks';
import { PictureOf } from './PictureOf';

const meta: Meta = {
  title: 'Wiki/World/Picture of a record',
  component: PictureOf,
  // Rendered, not args: the component is generic in its resource's row, which args would widen.
  render: () => <PictureOf resource={people} id={'person-1'} />,
  parameters: { msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** A person's picture, added by link and saved through the person's own resource. */
export const AddedByLink: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole('button', { name: 'Add a picture by link' }));
    await userEvent.type(canvas.getByLabelText('Picture link'), 'https://example.org/mara.png');
    await userEvent.click(canvas.getByRole('button', { name: 'Save picture' }));
    await expect(await canvas.findByRole('img', { name: 'Picture of Mara Quill' })).toBeInTheDocument();
  },
};
