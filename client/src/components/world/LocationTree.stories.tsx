// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, within } from 'storybook/test';
import { PLACES } from './fixtures';
import { LocationTree } from './LocationTree';

const meta: Meta<typeof LocationTree> = {
  title: 'World/Location tree',
  component: LocationTree,
  args: { places: PLACES, hrefOf: (place) => `/w/w1/location/${place.id}` },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('link', { name: /The Gull/ })).toHaveAttribute('href', '/w/w1/location/l3');
  },
};
