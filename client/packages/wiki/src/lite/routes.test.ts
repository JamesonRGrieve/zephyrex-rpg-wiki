// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
/** The catch-all's routing: what isn't a wiki route answers 404 before any database is touched. */
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import type { PrismaClient } from '@prisma/client';
import { NextRequest } from 'next/server';
import { describe, expect, it } from 'vitest';
import { WIKI_LITE_RESOURCES, wikiLite } from '../lite';

const untouched = new Proxy({} as PrismaClient, {
  get: () => {
    throw new Error('the database was touched');
  },
});
const routes = wikiLite({ prisma: untouched });
const call = (method: 'GET' | 'POST' | 'PUT' | 'DELETE', wiki: string[]) =>
  routes[method](new NextRequest(`http://localhost/api/v1/${wiki.join('/')}`, { method }), { params: Promise.resolve({ wiki }) });

describe('wikiLite', () => {
  it('serves the sync, session reports and every record resource', () => {
    expect(WIKI_LITE_RESOURCES).toEqual(expect.arrayContaining(['world_entity', 'session_report', 'person', 'setting', 'property_kit']));
  });

  it.each([
    ['an unknown resource', 'GET', ['dragon']],
    ['an inherited key', 'GET', ['constructor']],
    ['a path past a record', 'GET', ['person', 'p1', 'more']],
    ['a method a collection has not', 'PUT', ['person']],
    ['a method the sync has not', 'POST', ['world_entity']],
  ] as const)('answers 404 for %s', async (_what, method, wiki) => {
    expect((await call(method, [...wiki])).status).toBe(404);
  });
});

describe('prisma-fragment.mjs', () => {
  it("finds the wiki app's copy of the fragment current", () => {
    const script = join(__dirname, '..', '..', 'scripts', 'prisma-fragment.mjs');
    expect(execFileSync(process.execPath, [script, join(__dirname, '..', '..', '..', '..', 'prisma', 'schema'), '--check'], { encoding: 'utf8' })).toMatch(/matches/);
  });
});
