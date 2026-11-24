// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { KnownFacts } from './KnownFacts';

const meta: Meta<typeof KnownFacts> = {
  title: 'Wiki/World/Known facts',
  component: KnownFacts,
  args: {
    title: 'Who knows',
    lines: [
      { id: 'f1', who: 'Tobin Reyes', text: 'She keeps a lantern lit every night.' },
      { id: 'f2', who: 'Ada Marsh', text: null },
    ],
    characters: [
      { id: 'person-2', name: 'Tobin Reyes' },
      { id: 'person-7', name: 'Ada Marsh' },
    ],
    onAdd: fn(async () => null),
    onRemove: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

/** The GM's view: who knows what, each removable, and a new fact added for a character. */
export const ForTheGm: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText('Knows of it')).toBeInTheDocument();
    await userEvent.type(canvas.getByLabelText('What they learned'), 'Her brother drowned.');
    await userEvent.click(canvas.getByRole('button', { name: 'Add known fact' }));
    await expect(args.onAdd).toHaveBeenCalledWith('person-2', 'Her brother drowned.');
    await userEvent.click(canvas.getByRole('button', { name: "Remove Ada Marsh's fact" }));
    await expect(args.onRemove).toHaveBeenCalled();
  },
};

/** A player's own view: what their character knows, read only. */
export const ForAPlayer: Story = {
  args: {
    title: 'What Tobin Reyes knows',
    lines: [{ id: 'f1', who: null, text: 'She keeps a lantern lit every night.' }],
    characters: undefined,
    onAdd: undefined,
    onRemove: undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('heading', { name: 'What Tobin Reyes knows' })).toBeInTheDocument();
    await expect(canvas.queryByRole('button')).not.toBeInTheDocument();
  },
};

export const NothingYet: Story = {
  args: { lines: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Nothing learned yet.')).toBeInTheDocument();
  },
};

export const Loading: Story = {
  args: { lines: undefined },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Loading what is known')).toBeInTheDocument();
  },
};
