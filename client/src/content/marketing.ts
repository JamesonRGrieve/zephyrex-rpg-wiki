// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The landing page's words. The layout is @zephyrex/marketing's; what it says is this app's.
 * The way in is the app itself (/w, the worlds); PLANNED lists what docs/DESIGN.md proposes and
 * never presents a feature as live. Say what's live in the lead and the FAQ, and move a feature
 * out of PLANNED only when it ships whole.
 */
import type { Faq, Feature, FooterColumn, Link } from '@zephyrex/marketing';

// The header's call to action (START) opens the app; the plan is one link beside it.
export const NAV: readonly Link[] = [
  { label: 'What is planned', href: '#planned' },
  { label: 'How it compares', href: '#compare' },
  { label: 'FAQ', href: '#faq' },
];

/** The way in: the worlds you keep (the visual audit found the page never led into the app). */
export const START: Link = { label: 'Open your settings', href: '/w' };

export const HERO = {
  title: 'Your world, written down',
  lead: 'A worldbuilding and campaign wiki: who, where, when, what happened and what is secret. Settings and campaigns with their places, people, organisations, items, journals, plot hooks, tags and relations are here now; the rest is being built.',
};

export const PLANNED: readonly Feature[] = [
  {
    id: 'entities',
    title: 'Every kind of thing in your world',
    summary: 'Characters, places, organisations, families, items, events, quests and more, each with its own page.',
    details: ['Type @ and a name to link anything', 'Posts, properties, tags and inventory on any page'],
    availability: 'everywhere',
  },
  {
    id: 'secrets',
    title: 'Secrets that stay secret',
    summary: 'Hide a page, a note, a field or one paragraph, and see exactly what each player sees.',
    details: ['"View as" any player or role', 'Inline secret blocks inside your writing'],
    availability: 'everywhere',
  },
  {
    id: 'time',
    title: 'Calendars and timelines',
    summary: 'Your own calendar, with its months, moons and seasons, and timelines that move the map with the story.',
    details: ['Eras, leap rules and intercalary days', 'Reminders on calendar dates'],
    availability: 'everywhere',
  },
  {
    id: 'places',
    title: 'Maps with pins that open pages',
    summary: 'Locations at every scale, from a star system to a room, and maps with layers, groups and pins.',
    details: ['A pin opens the place it marks', 'Maps published from the Zephyrex VTT'],
    availability: 'everywhere',
  },
  {
    id: 'story',
    title: 'Story, sessions and manuscripts',
    summary: 'Quests, plots and session reports linked to everything they mention, and a focus mode for writing.',
    details: ['Family trees and diplomacy webs', 'Statblocks inside articles'],
    availability: 'everywhere',
  },
  {
    id: 'public',
    title: 'Share it with your table',
    summary: 'Invite players with roles, and publish read-only public pages for your world.',
    details: ['Members, invitations and roles', 'Themed public pages'],
    availability: 'hosted',
  },
  {
    id: 'take-away',
    title: 'Yours to take away',
    summary: 'Import from Kanka and World Anvil, and export to Markdown, JSON and Foundry journals.',
    details: ['No lock-in', 'Revision history on every page'],
    availability: 'everywhere',
  },
];

export const COMPARE: readonly { point: string; us: string; them: string }[] = [
  { point: 'Feature set', us: 'Planned: full parity with both', them: 'Kanka and World Anvil each have their own' },
  { point: 'Self-hosted, one person', us: 'Planned: the whole app, free', them: 'Hosted only' },
  { point: 'Import your world', us: 'Planned: from Kanka and World Anvil', them: 'Their own formats' },
  { point: 'Licence', us: 'Open source under the AGPL', them: 'Closed source' },
];

export const FAQS: readonly Faq[] = [
  {
    question: 'Can I use it today?',
    answer: 'Partly. You can keep worlds with their places, people, organisations, items, journals, plot hooks, tags and relations. Maps, calendars, secrets and import are still being built; this page says when each arrives.',
  },
  {
    question: 'Will it read my Kanka or World Anvil world?',
    answer: 'That is the plan: import from Kanka through its API and from a World Anvil export.',
  },
  {
    question: 'Will it be free?',
    answer: 'The self-hosted edition, for one person, is planned as the whole app and free under the AGPL.',
  },
];

export const CLOSING = {
  title: 'A wiki for the world you are building',
  body: 'Start a world now, and come back as more ships.',
};

export const FOOTER: readonly FooterColumn[] = [
  {
    title: 'Learn',
    links: [
      { label: 'Worlds', href: '/w' },
      { label: 'Planned features', href: '#planned' },
      { label: 'FAQ', href: '#faq' },
    ],
  },
];
