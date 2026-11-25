// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * What a person's page calls them when the reader doesn't know their name (operator, 2026-11-25:
 * "Their character page should still work"): rpg-ai passes RecordPage `shownAs` (the person's
 * unnamed_as) for a person the party hasn't named, and the page titles them by it and keeps their
 * name out of everything it shows (lib/shownAs). None: the page names them as usual.
 */
import { createContext, type ReactElement, type ReactNode, useContext } from 'react';

const ShownAsContext = createContext<string | null>(null);

export function ShownAsProvider({ shownAs, children }: { shownAs: string | null; children: ReactNode }): ReactElement {
  return <ShownAsContext.Provider value={shownAs}>{children}</ShownAsContext.Provider>;
}

export function useShownAs(): string | null {
  return useContext(ShownAsContext);
}
