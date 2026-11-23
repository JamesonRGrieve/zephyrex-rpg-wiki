// SPDX-License-Identifier: AGPL-3.0-or-later
import { existsSync } from 'node:fs';
import path from 'path';
import type { StorybookConfig } from '@storybook/nextjs';

const APP_SRC = path.resolve(import.meta.dirname, '../src');
// The wiki's client package (S7), read from its source, as the app reads it.
const WIKI_SRC = path.resolve(import.meta.dirname, '../packages/wiki/src');
// public/ holds only what is fetched into it , so it may not exist.
const PUBLIC = path.resolve(import.meta.dirname, '../public');

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(js|jsx|mjs|ts|tsx|mdx)', '../packages/wiki/src/**/*.stories.@(js|jsx|mjs|ts|tsx|mdx)'],
  // Storybook 10 folds actions/controls/interactions/viewport into core; links, a11y and docs (the
  // MDX guide under packages/wiki/src/docs) remain as separate addons here.
  addons: ['@storybook/addon-links', '@storybook/addon-a11y', '@storybook/addon-docs'],
  framework: {
    name: '@storybook/nextjs',
    options: {},
  },
  // .storybook/public holds msw's service worker, which the page stories' mock back end runs in.
  staticDirs: existsSync(PUBLIC) ? ['../public', './public'] : ['./public'],
  core: {
    disableTelemetry: true,
  },
  webpackFinal: async (webpackConfig) => {
    webpackConfig.resolve = webpackConfig.resolve || {};
    // This app's `~/*` alias (tsconfig paths); the framework is a compiled package.
    webpackConfig.resolve.alias = { ...(webpackConfig.resolve.alias || {}), '~': APP_SRC, '@zephyrex-rpg/wiki': WIKI_SRC };
    return webpackConfig;
  },
};

export default config;
