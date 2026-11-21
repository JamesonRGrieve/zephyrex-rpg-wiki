// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { inOrder, PostList } from './PostList';

const post = (id: string, name: string, position: string, ordinal: number) => ({
  id,
  name,
  position,
  ordinal,
  entry: null,
  description: `About ${name}`,
});
const POSTS = [post('a', 'History', 'default', 1), post('b', 'Rumour', 'pinned_top', 0), post('c', 'Founding', 'default', 0)];

describe('inOrder', () => {
  it('puts pinned posts first, then by ordinal', () => {
    expect(inOrder(POSTS).map((one) => one.name)).toEqual(['Rumour', 'Founding', 'History']);
  });
});

describe('PostList', () => {
  it('lists the posts pinned first, marking the pinned one', () => {
    render(<PostList posts={POSTS} />);
    const items = within(screen.getByRole('list', { name: 'Posts' })).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('Rumour');
    expect(within(items[0]!).getByLabelText('Pinned')).toBeInTheDocument();
    expect(screen.getByText('About History')).toBeInTheDocument();
  });

  it('shows loading, a load failure with a retry, and no posts', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<PostList posts={undefined} />);
    expect(screen.getByText('Loading the posts')).toBeInTheDocument();
    rerender(<PostList posts={undefined} error={new Error('offline')} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
    rerender(<PostList posts={[]} />);
    expect(screen.getByText('No posts yet.')).toBeInTheDocument();
  });
});
