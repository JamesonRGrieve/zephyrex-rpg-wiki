// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useWikiBase } from './base';
import { wikiExtension } from './extension';

vi.mock('./pages/WorldsPage', () => ({ WorldsPage: () => <p>{`worlds under ${useWikiBase()}`}</p> }));
vi.mock('./pages/RecordPage', () => ({
  RecordPage: ({ world, kind, id }: { world: string; kind: string; id: string }) => <p>{`${useWikiBase()} ${world} ${kind} ${id}`}</p>,
}));

describe('wikiExtension', () => {
  it('mounts the pages under w by default, most specific first, paired with rpg_core', () => {
    const extension = wikiExtension();
    expect(extension.pages?.map((page) => page.path)).toEqual(['w', 'w/:world/taxonomy', 'w/:world/plot', 'w/:world/about', 'w/:world/:kind', 'w/:world/:kind/:id']);
    expect([extension.name, extension.serverExtension, extension.navItems]).toEqual(['rpg_core', 'rpg_core', [{ title: 'Settings', url: '/w' }]]);
  });

  it('mounts them under a base of the app’s choosing, and passes the route’s values to the page', () => {
    const extension = wikiExtension({ base: '/wiki/' });
    expect(extension.navItems).toEqual([{ title: 'Settings', url: '/wiki' }]);
    const [worlds, , , , , record] = extension.pages ?? [];
    const Worlds = worlds!.component;
    const Record = record!.component;
    render(<Worlds params={{}} searchParams={{}} />);
    expect(screen.getByText('worlds under /wiki')).toBeInTheDocument();
    render(<Record params={{ world: 'w1', kind: 'person', id: 'p1' }} searchParams={{}} />);
    expect(screen.getByText('/wiki w1 person p1')).toBeInTheDocument();
  });
});
