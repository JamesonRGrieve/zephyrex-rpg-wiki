// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The end-to-end suite. For now one project, `lite`: this app's own API routes on a throwaway
 * SQLite file (migrated before the server starts), as a production build in its own build
 * directory, so it runs beside a dev server. The SaaS project joins when the wiki's server has an
 * e2e entry point (as zephyrex-rpg-ai's e2e_server.py).
 *
 *   VISUAL_AUDIT=<dir> playwright test e2e/audit.spec.ts
 */
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

// The wiki's e2e port block on the runners: 48000 + 10 × its 58137 lane (8), so 48080–48089.
export const PORTS = { lite: 48080 } as const;
const host = (port: number) => `http://127.0.0.1:${port}`;
const scratch = mkdtempSync(path.join(process.env.E2E_SCRATCH ?? tmpdir(), 'rpg-wiki-e2e-'));
const NEXT = './node_modules/.bin/next';
const PRISMA = './node_modules/.bin/prisma';
// E2E_REUSE_BUILD=1: start from the build already in the build directory, if there is one.
const REUSE_BUILD = process.env.E2E_REUSE_BUILD === '1';
const DIST = '.next-e2e-lite';

const lite = {
  NEXT_TELEMETRY_DISABLED: '1',
  RPG_WIKI_VARIANT: 'lite',
  NEXT_DIST_DIR: DIST,
  PORT: String(PORTS.lite),
  DATABASE_URL: `file:${path.join(scratch, 'lite.db')}`,
};

export default defineConfig({
  testDir: './e2e',
  // One local person and one database: the specs run one at a time.
  workers: 1,
  fullyParallel: false,
  reporter: [['list']],
  timeout: 60_000,
  use: { trace: 'off' },
  projects: [{ name: 'lite', use: { ...devices['Desktop Chrome'], baseURL: host(PORTS.lite) } }],
  webServer: [
    {
      command: `${PRISMA} migrate deploy && ${REUSE_BUILD ? `(test -f ${DIST}/BUILD_ID || ${NEXT} build)` : `${NEXT} build`} && ${NEXT} start -p ${PORTS.lite} -H 127.0.0.1`,
      url: `${host(PORTS.lite)}/api/v1/extension`,
      env: lite,
      timeout: 300_000,
      reuseExistingServer: false,
      stdout: 'pipe',
    },
  ],
});
