// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, within } from 'storybook/test';
import { TaxonChips } from './TaxonChips';

const meta: Meta<typeof TaxonChips> = {
  title: 'Wiki/World/Taxon chips',
  component: TaxonChips,
  args: {
    status: { id: 's1', name: 'Alive', kind: 'entity_status', colour: '#32a852', href: null },
    taxa: [
      { id: 't1', name: 'Nobility', kind: 'tag', colour: '#a83232', href: '/w/salt/taxonomy?taxon=t1' },
      { id: 't2', name: 'Elf', kind: 'race', colour: null, href: '/w/salt/taxonomy?taxon=t2' },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const tags = within(within(canvasElement).getByRole('list', { name: 'Tags' }));
    await expect(tags.getByRole('link', { name: 'Nobility' })).toBeInTheDocument();
  },
};

export const Unclassified: Story = {
  args: { status: null, taxa: [] },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText('No tags or status yet.')).toBeInTheDocument();
  },
};

export const LoadFailed: Story = {
  args: { status: undefined, taxa: undefined, error: new Error('The server did not answer'), onRetry: fn(() => Promise.resolve()) },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  },
};
