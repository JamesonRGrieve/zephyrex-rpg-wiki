// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { withSignedIn, withZephyrexApi } from 'zephyrex/testing';
import { CAMPAIGN_ID, PLAYTHROUGH_ID, wikiHandlers } from '../testing/wiki.mocks';
import { RecordPage } from './RecordPage';

const meta: Meta<typeof RecordPage> = {
  title: 'Wiki/Pages/Record',
  component: RecordPage,
  args: { world: CAMPAIGN_ID, kind: 'person', id: 'person-1' },
  parameters: { layout: 'fullscreen', msw: { handlers: wikiHandlers() } },
  // A signed-in session: the framework reads the extension list (capabilities) only for one.
  decorators: [withZephyrexApi, withSignedIn],
};
export default meta;
type Story = StoryObj<typeof meta>;

/** A person's page: who they are, where they stand, and their panels. */
export const Person: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Mara Quill' })).toBeInTheDocument();
    await expect(await canvas.findByText('Keeps the Lantern House.')).toBeInTheDocument();
  },
};

/** A hook's page. */
export const Hook: Story = {
  args: { kind: 'hook', id: 'hook-1' },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByRole('heading', { level: 1, name: 'Who lit the lighthouse?' })).toBeInTheDocument();
  },
};

/** A place's page. */
export const Place: Story = {
  args: { kind: 'location', id: 'location-3' },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByRole('heading', { level: 1, name: 'The Lantern House' })).toBeInTheDocument();
  },
};

/** A player's character reads it (rpg-ai's drawer for a player's seat): the public entry and the
 * public properties only, read only, with no lorebook keys, GM sections or GM panels. */
export const PlayerView: Story = {
  args: { viewer: { personId: 'person-2' } },
  parameters: {
    msw: {
      handlers: wikiHandlers({ properties: { 'person-1': [{ key: 'Role', value: 'Innkeeper' }, { key: 'True name', value: 'Mara Vane', is_private: true }] } }),
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Mara Quill' })).toBeInTheDocument();
    await expect(await canvas.findByText('Innkeeper')).toBeInTheDocument();
    await expect(canvas.getByText('Keeps the Lantern House.')).toBeInTheDocument();
    await expect(canvas.queryByText('She lit the lighthouse herself.')).not.toBeInTheDocument();
    await expect(canvas.queryByText('Mara Vane')).not.toBeInTheDocument();
    await expect(canvas.queryByText('Lorebook keys')).not.toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: 'Edit origin' })).not.toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: 'Elevate to scenario' })).not.toBeInTheDocument();
    // What their character has learned, read only.
    await expect(await canvas.findByRole('heading', { name: 'What Tobin Reyes knows' })).toBeInTheDocument();
    await expect(canvas.getByText('Mara keeps the lamp oil in the cellar.')).toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: 'Add known fact' })).not.toBeInTheDocument();
  },
};

/** The same page for the GM: the GM section, private properties and the lorebook keys show. */
export const GmView: Story = {
  parameters: {
    msw: { handlers: wikiHandlers({ properties: { 'person-1': [{ key: 'True name', value: 'Mara Vane', is_private: true }] } }) },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText('She lit the lighthouse herself.')).toBeInTheDocument();
    await expect(await canvas.findByText('Mara Vane')).toBeInTheDocument();
    await expect(canvas.getByText('Lorebook keys')).toBeInTheDocument();
    // Who knows what about her, and a fact added for one of the campaign's characters.
    await expect(await canvas.findByRole('heading', { name: 'Who knows' })).toBeInTheDocument();
    await expect(await canvas.findByText('Tobin Reyes:')).toBeInTheDocument();
    await expect(await canvas.findByRole('button', { name: 'Add known fact' })).toBeInTheDocument();
  },
};

/** A record kept to the GM that the player's character knows of (a known fact with no text): open to them. */
export const KnownOfByTheirCharacter: Story = {
  args: { id: 'person-3', viewer: { personId: 'person-2' } },
  parameters: {
    msw: {
      handlers: wikiHandlers({
        gmOnly: ['person-3'],
        rows: { known_fact: [{ id: 'known_fact-9', person_id: 'person-2', target_entity_type: 'person', target_entity_id: 'person-3', text: null, campaign_id: CAMPAIGN_ID }] },
      }),
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole('heading', { level: 1, name: 'Harbourmaster Vell' })).toBeInTheDocument();
    await expect(await canvas.findByText('Holds the keys to every boat.')).toBeInTheDocument();
  },
};

/** A record kept to the GM, opened by a player: nothing of it shows. */
export const KeptToTheGm: Story = {
  args: { id: 'person-3', viewer: { personId: 'person-2' } },
  parameters: { msw: { handlers: wikiHandlers({ gmOnly: ['person-3'] }) } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText('This is the GM’s, not something your character knows.')).toBeInTheDocument();
    await expect(canvas.queryByText('Holds the keys to every boat.')).not.toBeInTheDocument();
  },
};

/** A hook is the GM's: a player sees none of it. */
export const HookForAPlayer: Story = {
  args: { kind: 'hook', id: 'hook-1', viewer: { personId: 'person-2' } },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByRole('heading', { level: 1, name: 'Kept to the GM' })).toBeInTheDocument();
  },
};

/** A playthrough's person the scenario already has by name: nothing to elevate. */
export const AlreadyInTheScenario: Story = {
  args: { world: PLAYTHROUGH_ID, id: 'person-5' },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText('Copied in at start.')).toBeInTheDocument();
    await expect(canvas.queryByRole('button', { name: 'Elevate to scenario' })).not.toBeInTheDocument();
  },
};

/** A person made in play, whom the scenario lacks: the GM can elevate them. */
export const MadeInPlay: Story = {
  args: { world: PLAYTHROUGH_ID, id: 'person-6' },
  play: async ({ canvasElement }) => {
    await expect(await within(canvasElement).findByRole('button', { name: 'Elevate to scenario' })).toBeInTheDocument();
  },
};
