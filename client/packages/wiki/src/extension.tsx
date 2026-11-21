// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The wiki as a client extension (S7), for an app that composes it (rpg-ai's Together mode): its
 * pages under `base` ("w" by default), and a menu entry. It pairs with the server's rpg_core; each
 * section still shows only when `GET /v1/extension` lists the extension that serves it. Not a client
 * module: an app's config, which builds this, is read on the server too; the pages are client ones.
 */
import type { ComponentType, ReactElement } from 'react';
import type { ZephyrexClientExtension } from 'zephyrex';
import { WikiBaseProvider } from './base';
import { KindPage } from './pages/KindPage';
import { PlotPage } from './pages/PlotPage';
import { RecordPage } from './pages/RecordPage';
import { TaxonomyPage } from './pages/TaxonomyPage';
import { WorldsPage } from './pages/WorldsPage';

type RoutedProps = { params: Record<string, string>; searchParams: Record<string, string> };

/** A page under the router: its parameters as props, under the extension's base. */
function routed(base: string, render: (params: Record<string, string>) => ReactElement): ComponentType<RoutedProps> {
  function WikiRoute({ params }: RoutedProps): ReactElement {
    return <WikiBaseProvider base={base}>{render(params)}</WikiBaseProvider>;
  }
  return WikiRoute;
}

const of = (params: Record<string, string>, name: string): string => params[name] ?? '';

export interface WikiExtensionOptions {
  /** Where the pages live: "w" by default. */
  base?: string;
}

export function wikiExtension({ base = 'w' }: WikiExtensionOptions = {}): ZephyrexClientExtension {
  const root = base.replace(/^\/+|\/+$/g, '');
  return {
    name: 'rpg_core',
    serverExtension: 'rpg_core',
    displayName: 'Zephyrex RPG Wiki',
    description: 'Worlds and their places, people, organisations, items, journals and plot',
    // Most specific first: the router takes the first pattern that matches.
    pages: [
      { path: root, component: routed(root, () => <WorldsPage />) },
      { path: `${root}/:world/taxonomy`, component: routed(root, (params) => <TaxonomyPage world={of(params, 'world')} />) },
      { path: `${root}/:world/plot`, component: routed(root, (params) => <PlotPage world={of(params, 'world')} />) },
      { path: `${root}/:world/:kind`, component: routed(root, (params) => <KindPage world={of(params, 'world')} kind={of(params, 'kind')} />) },
      {
        path: `${root}/:world/:kind/:id`,
        component: routed(root, (params) => <RecordPage world={of(params, 'world')} kind={of(params, 'kind')} id={of(params, 'id')} />),
      },
    ],
    navItems: [{ title: 'Worlds', url: `/${root}` }],
  };
}
