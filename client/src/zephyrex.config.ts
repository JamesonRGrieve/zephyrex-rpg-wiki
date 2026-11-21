// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ZephyrexConfig } from 'zephyrex';
import { wikiExtension } from '@zephyrex-rpg/wiki/extension';
import { genealogyExtension } from './extensions/campaign';

export const APP_NAME = 'Zephyrex RPG Wiki';
export const APP_DESCRIPTION = 'A worldbuilding and campaign wiki: who, where, when, what happened and what is secret.';

/** The app's pages (matched as path prefixes); in the hosted build they need a signed-in person. */
const APP_ROUTES = ['/w', '/settings', '/team'];

/**
 * The build edition decides only what the back end can do, never what a page shows: pages turn a
 * feature on when `GET /v1/extension` lists the extension that serves it. The hosted (saas) build
 * has accounts. The lite build is one person's app with no sign-in, where "View as" stands in for
 * players (docs/DESIGN.md, Editions), so auth is off in lite only.
 *
 * The config is imported on the client (app/Providers.tsx) and by the middleware.
 */
const HOSTED = process.env.NEXT_PUBLIC_RPG_WIKI_VARIANT === 'saas';

const DEFAULT_PORT = 1109;

const config: ZephyrexConfig = {
  server: {
    // Same-origin: the browser calls `/api/v1/...` on this app, answered by its own lite handlers
    // or, in the hosted build, proxied to server/ (next.config.js).
    baseUrl: '/api',
    ...(HOSTED
      ? { upstreamUrl: process.env.RPG_WIKI_SERVER_URI || 'http://127.0.0.1:2000' }
      : { upstreamUrl: process.env.API_UPSTREAM_URL || `http://127.0.0.1:${process.env.PORT || DEFAULT_PORT}/api` }),
  },
  app: {
    name: APP_NAME,
    description: APP_DESCRIPTION,
    defaultTheme: 'dark',
    // Never send a signed-in person's email hash to Gravatar: no request leaves for a third party.
    gravatar: false,
  },
  auth: HOSTED ? { enabled: true, privateRoutes: APP_ROUTES } : { enabled: false },
  // The wiki's own pages, as an app composing the wiki registers them (S7); genealogy is the
  // framework's people.
  extensions: [wikiExtension(), genealogyExtension],
};

export default config;
