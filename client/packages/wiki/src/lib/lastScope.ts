// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The setting or campaign the person was last in, remembered in this browser, so the sidebar's
 * Places, People… open there (operator, 2026-11-21). A scope as the pages take it (lib/scope).
 */
const KEY = 'zephyrex-rpg-wiki:last-scope';

export function rememberScope(scope: string): void {
  try {
    window.localStorage.setItem(KEY, scope);
  } catch {
    // Storage refused (private mode): the sidebar opens Settings instead.
  }
}

export function lastScope(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}
