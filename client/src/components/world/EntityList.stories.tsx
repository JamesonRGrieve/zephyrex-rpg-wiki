// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { LOCATION_KINDS } from '~/contract';
import { EntityList } from './EntityList';
import { PLACES } from './fixtures';
import { ParentTree } from './ParentTree';

const hrefOf = (row: { id: string }) => `/w/w1/location/${row.id}`;

const meta: Meta<typeof EntityList<(typeof PLACES)[number]>> = {
  title: 'World/Entity list',
  component: EntityList,
  args: {
    what: 'place',
    plural: 'places',
    rows: PLACES,
    kinds: LOCATION_KINDS,
    hrefOf,
    onCreate: fn(() => Promise.resolve(true)),
    onDelete: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByRole('searchbox', { name: 'Find places' }), 'port');
    await expect(canvas.getByRole('link', { name: /Saltmarsh/ })).toBeInTheDocument();
  },
};

export const WithTree: Story = {
  args: { aside: <ParentTree rows={PLACES} label='Places by where they sit' hrefOf={hrefOf} /> },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('navigation', { name: 'Places by where they sit' })).toBeInTheDocument();
  },
};

export const Loading: Story = {
  args: { rows: undefined },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('Loading places')).toBeInTheDocument();
  },
};

export const LoadFailed: Story = {
  args: { rows: undefined, error: new Error('The server did not answer'), onRetry: fn(() => Promise.resolve()) },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  },
};

export const FirstRun: Story = {
  args: { rows: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText(/Add the first one above/)).toBeInTheDocument();
  },
};
