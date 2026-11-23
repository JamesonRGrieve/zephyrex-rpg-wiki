// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, within } from 'storybook/test';
import { PostList } from './PostList';

const meta: Meta<typeof PostList> = {
  title: 'Wiki/World/Post list',
  component: PostList,
  args: {
    posts: [
      { id: 'a', name: 'History', position: 'default', ordinal: 1, entry: null, description: 'Founded by smugglers.' },
      { id: 'b', name: 'Rumour', position: 'pinned_top', ordinal: 0, entry: null, description: 'The guild hides a vault.' },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const items = within(within(canvasElement).getByRole('list', { name: 'Posts' })).getAllByRole('listitem');
    await expect(items[0]).toHaveTextContent('Rumour');
  },
};

export const NoPosts: Story = {
  args: { posts: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No posts yet.')).toBeInTheDocument();
  },
};

export const LoadFailed: Story = {
  args: { posts: undefined, error: new Error('The server did not answer'), onRetry: fn(() => Promise.resolve()) },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  },
};
