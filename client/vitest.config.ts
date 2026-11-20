// SPDX-License-Identifier: AGPL-3.0-or-later
import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    // The framework's jsdom stand-ins and toast reset first, then this app's mocks.
    setupFiles: ['zephyrex/testing/setup', 'src/__tests__/setup.ts'],
    // Forks, Vitest's default: on a loaded runner (58133, load ~50) a threads worker loading jsdom and
    // the framework took longer to start than Vitest's fixed 60 s worker timeout, and no test ran;
    // under forks the same file passed (2026-11-20).
    pool: 'forks',
    // A runner job sets VITEST_MAX_WORKERS to its granted cores (standards page Gates).
    globals: true,
    exclude: ['**/node_modules/**', '.next/**', 'e2e/**', '**/*.stories.{ts,tsx}'],
  },
  resolve: {
    alias: {
      // Mirrors the tsconfig `~/*` path to this app's source.
      '~': path.resolve(__dirname, './src'),
    },
  },
});
