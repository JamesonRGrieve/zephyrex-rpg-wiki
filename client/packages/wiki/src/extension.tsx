// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The wiki as a client extension (S7), for an app that composes it (rpg-ai's Together mode): its
 * pages under `base` ("w" by default), and a menu entry. It pairs with the server's rpg_core; each
 * section still shows only when `GET /v1/extension` lists the extension that serves it. Not a client
 * module: an app's config, which builds this, is read on the server too; the pages are client ones.
 */
import type { ComponentType, ReactElement } from 'react';
import type { ZephyrexClientExtension } from 'zephyrex';
import { type SettingSections, SettingSectionsProvider, WikiBaseProvider } from './base';
import { KindPage } from './pages/KindPage';
import { LastScopePage, lastScopePath } from './pages/LastScopePage';
import { useLastScope } from './lib/lastScope';
import { PlotPage } from './pages/PlotPage';
import { RecordPage } from './pages/RecordPage';
import { TaxonomyPage } from './pages/TaxonomyPage';
import { WorldPage } from './pages/WorldPage';
import { WorldsPage } from './pages/WorldsPage';
import { wikiRoot } from './lib/paths';

type RoutedProps = { params: Record<string, string>; searchParams: Record<string, string> };

/** A page under the router: its parameters as props, under the extension's base. */
function routed(base: string, render: (params: Record<string, string>) => ReactElement, sections: SettingSections = []): ComponentType<RoutedProps> {
  function WikiRoute({ params }: RoutedProps): ReactElement {
    return (
      <WikiBaseProvider base={base}>
        <SettingSectionsProvider sections={sections}>{render(params)}</SettingSectionsProvider>
      </WikiBaseProvider>
    );
  }
  return WikiRoute;
}

const of = (params: Record<string, string>, name: string): string => params[name] ?? '';

/** A sidebar sub-entry, as a nav item's useChildren gives it (the framework's NavChild). */
type NavChild = { title: string; url: string };

/** The sidebar's entries under Settings, in order: each a kind of page (or the plot board, or game systems). */
export const SETTINGS_ENTRIES: readonly (readonly [string, string])[] = [
  ['Places', 'location'],
  ['People', 'person'],
  ['Organisations', 'faction'],
  ['Items', 'item'],
  ['Lore', 'journal'],
  ['Plot', 'plot'],
  ['Game systems', 'systems'],
];

/** The Settings entry's useChildren: made once per extension (a stable hook for the sidebar). */
function settingsChildren(base: string): () => readonly NavChild[] {
  return function useSettingsChildren(): readonly NavChild[] {
    const scope = useLastScope();
    return SETTINGS_ENTRIES.map(([title, kind]) => ({ title, url: lastScopePath(base, scope, kind) }));
  };
}

export interface WikiExtensionOptions {
  /** Where the pages live: "w" by default. */
  base?: string;
  /** Sections the app adds to each setting (VTT's game systems), each rendered with the setting's id; each gates itself by capability. */
  settingSections?: SettingSections;
}

export function wikiExtension({ base = 'w', settingSections = [] }: WikiExtensionOptions = {}): ZephyrexClientExtension {
  const root = wikiRoot(base).slice(1);
  return {
    name: 'rpg_core',
    serverExtension: 'rpg_core',
    displayName: 'Zephyrex RPG Wiki',
    description: 'Settings and campaigns: their places, people, organisations, items, journals and plot',
    // Most specific first: the router takes the first pattern that matches.
    pages: [
      { path: root, component: routed(root, () => <WorldsPage />, settingSections) },
      { path: `${root}/last/:kind`, component: routed(root, (params) => <LastScopePage kind={of(params, 'kind')} />, settingSections) },
      { path: `${root}/:world/taxonomy`, component: routed(root, (params) => <TaxonomyPage world={of(params, 'world')} />, settingSections) },
      { path: `${root}/:world/plot`, component: routed(root, (params) => <PlotPage world={of(params, 'world')} />, settingSections) },
      { path: `${root}/:world/about`, component: routed(root, (params) => <WorldPage world={of(params, 'world')} />, settingSections) },
      { path: `${root}/:world/:kind`, component: routed(root, (params) => <KindPage world={of(params, 'world')} kind={of(params, 'kind')} />, settingSections) },
      {
        path: `${root}/:world/:kind/:id`,
        component: routed(root, (params) => <RecordPage world={of(params, 'world')} kind={of(params, 'kind')} id={of(params, 'id')} />, settingSections),
      },
    ],
    // Settings, and under it each kind of page in the setting or campaign last shown, computed as
    // the sidebar renders (useChildren), so they follow the person as they move.
    navItems: [{ title: 'Settings', url: `/${root}`, useChildren: settingsChildren(`/${root}`) }],
  };
}
