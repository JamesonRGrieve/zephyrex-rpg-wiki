// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** A world's own pages: all worlds, its about page, each kind's list, its taxonomy and plot board. */
import Link from 'next/link';
import type { ReactElement } from 'react';
import { useWikiBase } from '../../base';
import { useCapabilities } from '../../features/capabilities';
import { aboutPath, kindPath, plotPath, taxonomyPath } from '../../lib/paths';
import { ENTITY_KINDS } from './kinds';

const LINK = 'underline-offset-4 hover:underline aria-[current=page]:font-semibold';

export function WorldNav({ world, current }: { world: string; current: string }): ReactElement {
  const base = useWikiBase();
  const can = useCapabilities();
  return (
    <nav aria-label='This world' className='flex flex-wrap gap-x-4 gap-y-2 text-sm'>
      <Link href={base} className='underline-offset-4 hover:underline'>
        All worlds
      </Link>
      <Link href={aboutPath(base, world)} aria-current={current === 'about' ? 'page' : undefined} className={LINK}>
        About
      </Link>
      {Object.entries(ENTITY_KINDS).map(([path, one]) => (
        <Link key={path} href={kindPath(base, world, path)} aria-current={path === current ? 'page' : undefined} className={LINK}>
          {one.title}
        </Link>
      ))}
      {can.taxonomy && (
        <Link href={taxonomyPath(base, world)} aria-current={current === 'taxonomy' ? 'page' : undefined} className={LINK}>
          Taxonomy
        </Link>
      )}
      {can.hooks && (
        <Link href={plotPath(base, world)} aria-current={current === 'plot' ? 'page' : undefined} className={LINK}>
          Plot board
        </Link>
      )}
    </nav>
  );
}
