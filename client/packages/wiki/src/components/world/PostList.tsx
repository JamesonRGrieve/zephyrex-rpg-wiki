// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The posts on a record (W3): pinned ones first, then by their order, each with its title and text.
 * Read here; who sees which post is acl_rbac's (W9). Four states, as every data view.
 */
import { Pin } from 'lucide-react';
import type { ReactElement } from 'react';
import { LoadProblem } from 'zephyrex/ui/load-problem';
import { SkeletonRows } from 'zephyrex/ui/skeleton';
import { keyed, linesOf } from './EntityPage';

export interface PostRow {
  id: string;
  name: string;
  entry: string | null;
  description: string | null;
  position: string | null;
  ordinal: number | null;
}

/** Pinned first, then by ordinal, then by name. */
export function inOrder<T extends PostRow>(rows: readonly T[]): T[] {
  const pinned = (row: T) => (row.position === 'pinned_top' ? 0 : 1);
  return [...rows].sort((a, b) => pinned(a) - pinned(b) || (a.ordinal ?? 0) - (b.ordinal ?? 0) || a.name.localeCompare(b.name));
}

export function PostList({
  posts,
  error,
  onRetry,
}: {
  posts: readonly PostRow[] | undefined;
  error?: Error;
  onRetry?: () => Promise<unknown>;
}): ReactElement {
  return (
    <section aria-labelledby='posts-title' className='space-y-3'>
      <h2 id='posts-title' className='text-lg font-semibold'>
        Posts
      </h2>
      {error !== undefined && <LoadProblem what='the posts' error={error} onRetry={onRetry} />}
      {posts === undefined && error === undefined && <SkeletonRows rows={2} label='Loading the posts' />}
      {posts !== undefined && posts.length === 0 && <p className='text-sm text-muted-foreground'>No posts yet.</p>}
      {posts !== undefined && posts.length > 0 && (
        <ul aria-label='Posts' className='space-y-3'>
          {inOrder(posts).map((post) => (
            <li key={post.id} className='rounded-xl border p-4'>
              <h3 className='flex items-center gap-2 font-medium'>
                {post.position === 'pinned_top' && <Pin className='size-4 text-muted-foreground' aria-label='Pinned' />}
                {post.name}
              </h3>
              {keyed(linesOf(post.entry, post.description).filter((line) => line.trim() !== '')).map(({ key, line }) => (
                <p key={key} className='mt-2 text-sm'>
                  {line}
                </p>
              ))}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
