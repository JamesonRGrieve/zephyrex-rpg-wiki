// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ZephyrexConfig } from 'zephyrex';
import { genealogyExtension, rpgLogExtension } from './extensions/campaign';
import { rpgExtension } from './extensions/rpg';

const config: ZephyrexConfig = {
  server: {
    baseUrl: process.env.NEXT_PUBLIC_API_URI ?? 'http://localhost:2000',
  },
  app: {
    name: 'Zephyrex RPG Wiki',
    description: 'Worldbuilding and campaign wiki on the Zephyrex framework',
    defaultTheme: 'dark',
  },
  auth: {
    privateRoutes: ['/rpg', '/settings', '/team'],
  },
  extensions: [rpgExtension, genealogyExtension, rpgLogExtension],
};

export default config;
