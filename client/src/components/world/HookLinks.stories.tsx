// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, within } from 'storybook/test';
import { HookLinks } from './HookLinks';

const meta: Meta<typeof HookLinks> = {
  title: 'World/Hook links',
  component: HookLinks,
  args: {
    waitsOn: [{ id: 'find', name: 'Find the map', href: '/w/salt/hook/find' }],
    leadsTo: [{ id: 'slay', name: 'Slay the wyrm', href: '/w/salt/hook/slay' }],
    takers: [
      { id: 'p1', name: 'Hunter Brin', href: '/w/salt/person/brin', status: 'active', progress: 3 },
      { id: 'f1', name: 'Hunters’ Lodge', href: '/w/salt/faction/lodge', status: 'available', progress: null },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(within(canvas.getByRole('list', { name: 'Waits on' })).getByRole('link', { name: 'Find the map' })).toBeInTheDocument();
    await expect(canvas.getByText('active · 3')).toBeInTheDocument();
  },
};

export const Unlinked: Story = {
  args: { waitsOn: [], leadsTo: [], takers: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No one yet.')).toBeInTheDocument();
  },
};

export const LoadFailed: Story = {
  args: { waitsOn: undefined, leadsTo: undefined, takers: undefined, error: new Error('The server did not answer'), onRetry: fn(() => Promise.resolve()) },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  },
};
