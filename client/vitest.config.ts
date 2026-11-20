// SPDX-License-Identifier: AGPL-3.0-or-later
import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    // The framework's jsdom stand-ins and toast reset first, then this app's mocks.
    setupFiles: ['zephyrex/testing/setup', 'src/__tests__/setup.ts'],
    // Forks, Vitest's default. Neither pool beats load: on 58133 at load ~50-70, on two niced cores,
    // threads and then forks workers loading jsdom and the framework each missed Vitest's fixed 60 s
    // start timeout and no test ran (2026-11-20). That is load: re-run on a quieter runner.
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
