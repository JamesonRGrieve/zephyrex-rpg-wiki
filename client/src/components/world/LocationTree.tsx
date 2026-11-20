// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A world's places as the tree they form: each under its parent, siblings by name. A place whose
 * parent isn't among the rows (another world's, or deleted) stands at the top.
 */
import Link from 'next/link';
import type { ReactElement } from 'react';
import type { Place } from '~/features/data/records';

export interface PlaceNode {
  place: Place;
  children: PlaceNode[];
}

/** The rows as a forest: roots first, each node's children sorted by name. */
export function treeOf(places: readonly Place[]): PlaceNode[] {
  const nodes = new Map(places.map((place) => [place.id, { place, children: [] as PlaceNode[] }]));
  const roots: PlaceNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.place.parent_id === null ? undefined : nodes.get(node.place.parent_id);
    (parent === undefined ? roots : parent.children).push(node);
  }
  const byName = (a: PlaceNode, b: PlaceNode) => a.place.name.localeCompare(b.place.name);
  const sort = (list: PlaceNode[]) => {
    list.sort(byName);
    for (const node of list) sort(node.children);
  };
  sort(roots);
  return roots;
}

function Branch({ nodes, hrefOf }: { nodes: readonly PlaceNode[]; hrefOf: (place: Place) => string }): ReactElement {
  return (
    <ul className='space-y-1 border-l pl-4 first:border-l-0 first:pl-0'>
      {nodes.map(({ place, children }) => (
        <li key={place.id}>
          <Link href={hrefOf(place)} className='inline-flex min-h-11 items-center gap-2 rounded-md px-2 hover:bg-accent'>
            <span className='font-medium'>{place.name}</span>
            {/* A real space, so the link reads "Saltmarsh city", not "Saltmarshcity". */}
            {place.kind !== null && (
              <>
                {' '}
                <span className='text-xs text-muted-foreground'>{place.kind.replaceAll('_', ' ')}</span>
              </>
            )}
          </Link>
          {children.length > 0 && <Branch nodes={children} hrefOf={hrefOf} />}
        </li>
      ))}
    </ul>
  );
}

export function LocationTree({ places, hrefOf }: { places: readonly Place[]; hrefOf: (place: Place) => string }): ReactElement {
  return (
    <nav aria-label='Places by where they sit'>
      <Branch nodes={treeOf(places)} hrefOf={hrefOf} />
    </nav>
  );
}
