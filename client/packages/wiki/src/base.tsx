// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * Where the wiki's pages live in the app that shows them (S7): `/w` in the wiki's own app, and
 * whatever base an app composing the wiki mounts it at (`wikiExtension({ base })`). Every link the
 * pages build starts here.
 */
import { createContext, type ReactElement, type ReactNode, useContext } from 'react';
import { wikiRoot } from './lib/paths';

const WikiBase = createContext('/w');

/** The pages' base path, with a leading slash and none at the end: "/w". */
export function useWikiBase(): string {
  return useContext(WikiBase);
}

/** Mounts the pages under `base` ("w", "/wiki", …). */
export function WikiBaseProvider({ base, children }: { base: string; children: ReactNode }): ReactElement {
  return <WikiBase.Provider value={wikiRoot(base)}>{children}</WikiBase.Provider>;
}
