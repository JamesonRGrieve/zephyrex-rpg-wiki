// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * @zephyrex-rpg/wiki/lite: the wiki's lite API for an app's own Next.js server (never 'use client').
 * `wikiLite({ prisma })` gives the catch-all route's handlers; WIKI_LITE_EXTENSIONS is what an app's
 * GET /v1/extension lists for them. See lite/routes.ts.
 */
export { WIKI_LITE_EXTENSIONS } from './lite/extensions';
export { WIKI_LITE_RESOURCES, wikiLite, type WikiLiteOptions } from './lite/routes';
export { onAfterInstantiate, type AfterInstantiate, type Instantiated } from './lite/afterInstantiate';
