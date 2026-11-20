// SPDX-License-Identifier: AGPL-3.0-or-later
// Which back end answers /api/v1/*. The UI is the same either way: it only ever calls the
// same-origin /api, so switching editions is a build-time config change (docs/DESIGN.md, Editions).
//   lite (default): the app's own `route.lite.ts` handlers (one person, self-hosted, Next.js only).
//   saas:           server/ (the zephyrex server framework), reached through a proxy.
const VARIANTS = ['lite', 'saas'];
const VARIANT = process.env.RPG_WIKI_VARIANT || 'lite';
if (!VARIANTS.includes(VARIANT)) {
  throw new Error(`RPG_WIKI_VARIANT must be one of ${VARIANTS.join(', ')}, got "${VARIANT}"`);
}
const IS_LITE = VARIANT === 'lite';

// The framework server the SaaS build proxies to (server-side only, never sent to the browser).
// Its routes live at /v1/*, so /api/v1/x maps to ${SERVER_URI}/v1/x.
const SERVER_URI = process.env.RPG_WIKI_SERVER_URI || 'http://127.0.0.1:2000';

const DEFAULT_PAGE_EXTENSIONS = ['tsx', 'ts', 'jsx', 'js'];

/** @type {import('next').NextConfig} */
module.exports = {
  // Lets a test build sit beside a running dev server without sharing its output.
  distDir: process.env.NEXT_DIST_DIR || '.next',
  ...(process.env.NEXT_OUTPUT_STANDALONE ? { output: 'standalone' } : {}),
  // `route.lite.ts` is a route only in the lite build; the SaaS build never sees it.
  pageExtensions: IS_LITE ? ['lite.ts', ...DEFAULT_PAGE_EXTENSIONS] : DEFAULT_PAGE_EXTENSIONS,
  env: {
    NEXT_PUBLIC_RPG_WIKI_VARIANT: VARIANT,
  },
  async rewrites() {
    if (IS_LITE) {
      return [];
    }
    // beforeFiles, so the app-root [...slug] catch-all page never claims an API path.
    return { beforeFiles: [{ source: '/api/v1/:path*', destination: `${SERVER_URI}/v1/:path*` }] };
  },
};
