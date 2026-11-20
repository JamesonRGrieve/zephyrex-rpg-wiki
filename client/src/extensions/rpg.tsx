// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';

import type { ZephyrexClientExtension } from 'zephyrex';

function RPGDashboard() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Zephyrex RPG Wiki</h1>
      <p>Worldbuilding and campaign wiki on the Zephyrex framework: entities, lore, secrets, timelines, maps, history.</p>
    </div>
  );
}

function RPGSettings() {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-2">RPG Settings</h2>
      <p>Configure your campaign extensions.</p>
    </div>
  );
}

export const rpgExtension: ZephyrexClientExtension = {
  name: 'rpg',
  displayName: 'Zephyrex RPG Wiki',
  description: 'Entities, lore, secrets, timelines, maps, history',
  serverExtension: 'rpg_log',
  pages: [
    {
      path: 'rpg',
      component: RPGDashboard,
    },
  ],
  navItems: [
    {
      title: 'Zephyrex RPG Wiki',
      url: '/rpg',
    },
  ],
  settingsPanel: RPGSettings,
};
