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

/**
 * What an app composing the wiki adds to each setting (operator, 2026-11-21: game systems belong
 * under settings): components rendered in the setting's section and on its pages, given its id.
 * VTT's game systems component is the first; each gates itself by capability.
 */
export interface SettingSection {
  /** Its stable name (the section's key and anchor): "game-systems". */
  id: string;
  /** Its heading on the setting's page: "Game systems". */
  title: string;
  render: (settingId: string) => ReactNode;
}
export type SettingSections = readonly SettingSection[];

const SettingSectionsContext = createContext<SettingSections>([]);

export function useSettingSections(): SettingSections {
  return useContext(SettingSectionsContext);
}

export function SettingSectionsProvider({ sections, children }: { sections: SettingSections; children: ReactNode }): ReactElement {
  return <SettingSectionsContext.Provider value={sections}>{children}</SettingSectionsContext.Provider>;
}

/** Each of the app's sections for a setting, in the order given, under its own heading. */
export function SettingSectionsOf({ settingId }: { settingId: string }): ReactElement | null {
  const sections = useSettingSections();
  if (sections.length === 0) return null;
  return (
    <>
      {sections.map((section) => (
        <section key={section.id} aria-labelledby={`${section.id}-${settingId}`} className='grid gap-2'>
          <h3 id={`${section.id}-${settingId}`} className='text-base font-semibold'>
            {section.title}
          </h3>
          {section.render(settingId)}
        </section>
      ))}
    </>
  );
}
