// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * Who is reading a record page (rpg-ai's play drawer, operator 2026-11-24: "As a non-GM, only player
 * visible information and learned facts should be present there, not the whole GM file"): the GM,
 * who sees and edits everything, or a player's character, who sees what a player may: no GM-only
 * records, private properties, GM sections of an entry, dispositions, hooks' plot, lorebook keys or
 * edit controls. The wiki's own pages are the GM's.
 */
import { createContext, type ReactElement, type ReactNode, useContext } from 'react';

export type Viewer = 'gm' | { personId: string };

const ViewerContext = createContext<Viewer>('gm');

export function ViewerProvider({ viewer, children }: { viewer: Viewer; children: ReactNode }): ReactElement {
  return <ViewerContext.Provider value={viewer}>{children}</ViewerContext.Provider>;
}

export function useViewer(): Viewer {
  return useContext(ViewerContext);
}

/** Whether the reader is the GM (sees GM-only parts and may edit). */
export function useIsGm(): boolean {
  return useViewer() === 'gm';
}
