// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * The setting or campaign the person was last in, remembered in this browser, so the sidebar's
 * Places, People… open there (operator, 2026-11-21). A scope as the pages take it (lib/scope).
 */
import { useSyncExternalStore } from 'react';

const KEY = 'zephyrex-rpg-wiki:last-scope';
/** Told in this tab when the scope changes (the storage event reaches only other tabs). */
const CHANGED = 'zephyrex-rpg-wiki:last-scope-changed';

export function rememberScope(scope: string): void {
  try {
    if (window.localStorage.getItem(KEY) === scope) return;
    window.localStorage.setItem(KEY, scope);
    window.dispatchEvent(new Event(CHANGED));
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

function subscribe(onChange: () => void): () => void {
  const onStorage = (event: StorageEvent): void => {
    if (event.key === KEY) onChange();
  };
  window.addEventListener(CHANGED, onChange);
  window.addEventListener('storage', onStorage);
  return () => {
    window.removeEventListener(CHANGED, onChange);
    window.removeEventListener('storage', onStorage);
  };
}

/** The remembered scope, kept current as the person moves (in this tab or another); none on the server. */
export function useLastScope(): string | null {
  return useSyncExternalStore(subscribe, lastScope, () => null);
}
