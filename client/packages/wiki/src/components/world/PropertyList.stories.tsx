// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { PropertyList } from './PropertyList';

const meta: Meta<typeof PropertyList> = {
  title: 'Wiki/World/Property list',
  component: PropertyList,
  args: {
    rows: [
      { id: 'p1', key: 'Population', value: '9 billion', value_type: 'text', is_private: false },
      { id: 'p2', key: 'Garrison', value: '3', value_type: 'number', is_private: true },
      { id: 'p3', key: 'Shrine world', value: 'true', value_type: 'boolean', is_private: false },
      { id: 'p4', key: 'Founded', value: 'M38', value_type: 'date', is_private: false },
    ],
    onSave: fn(async () => null),
    onAdd: fn(async () => null),
    onRemove: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Reading: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText('9 billion')).toBeInTheDocument();
    await expect(canvas.queryByRole('button')).not.toBeInTheDocument();
  },
};

export const Editing: Story = {
  args: { canEdit: true },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Yes: Shrine world' }));
    await expect(args.onSave).toHaveBeenCalled();
    await userEvent.type(canvas.getByLabelText('New property'), 'Tithe grade');
    await userEvent.click(canvas.getByRole('button', { name: 'Add property' }));
    await expect(args.onAdd).toHaveBeenCalledWith('Tithe grade', 'text');
  },
};

export const Empty: Story = {
  args: { rows: [], canEdit: true },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No properties yet.')).toBeInTheDocument();
  },
};

export const Loading: Story = { args: { rows: undefined } };

export const Failed: Story = {
  args: { rows: undefined, error: new Error('The server could not be reached'), onRetry: fn(async () => undefined) },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('The server could not be reached')).toBeInTheDocument();
  },
};
