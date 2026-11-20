// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Records that sit under a parent, as the tree they form: places, and organisations and families.
 * Each under its parent, siblings by name. A record whose parent isn't among the rows (another
 * world's, or deleted) stands at the top.
 */
import Link from 'next/link';
import type { ReactElement } from 'react';

export interface TreeRow {
  id: string;
  name: string;
  kind: string | null;
  parent_id: string | null;
}

export interface TreeNode<T extends TreeRow> {
  row: T;
  children: TreeNode<T>[];
}

/** The rows as a forest: roots first, each node's children sorted by name. */
export function treeOf<T extends TreeRow>(rows: readonly T[]): TreeNode<T>[] {
  const nodes = new Map(rows.map((row) => [row.id, { row, children: [] as TreeNode<T>[] }]));
  const roots: TreeNode<T>[] = [];
  for (const node of nodes.values()) {
    const parent = node.row.parent_id === null ? undefined : nodes.get(node.row.parent_id);
    (parent === undefined ? roots : parent.children).push(node);
  }
  const sort = (list: TreeNode<T>[]) => {
    list.sort((a, b) => a.row.name.localeCompare(b.row.name));
    for (const node of list) sort(node.children);
  };
  sort(roots);
  return roots;
}

function Branch<T extends TreeRow>({ nodes, hrefOf }: { nodes: readonly TreeNode<T>[]; hrefOf: (row: T) => string }): ReactElement {
  return (
    <ul className='space-y-1 border-l pl-4 first:border-l-0 first:pl-0'>
      {nodes.map(({ row, children }) => (
        <li key={row.id}>
          <Link href={hrefOf(row)} className='inline-flex min-h-11 items-center gap-2 rounded-md px-2 hover:bg-accent'>
            <span className='font-medium'>{row.name}</span>
            {/* A real space, so the link reads "Saltmarsh city", not "Saltmarshcity". */}
            {row.kind !== null && (
              <>
                {' '}
                <span className='text-xs text-muted-foreground'>{row.kind.replaceAll('_', ' ')}</span>
              </>
            )}
          </Link>
          {children.length > 0 && <Branch nodes={children} hrefOf={hrefOf} />}
        </li>
      ))}
    </ul>
  );
}

export function ParentTree<T extends TreeRow>({
  rows,
  hrefOf,
  label,
}: {
  rows: readonly T[];
  hrefOf: (row: T) => string;
  /** The tree's name for assistive technology ("Places by where they sit"). */
  label: string;
}): ReactElement {
  return (
    <nav aria-label={label}>
      <Branch nodes={treeOf(rows)} hrefOf={hrefOf} />
    </nav>
  );
}
