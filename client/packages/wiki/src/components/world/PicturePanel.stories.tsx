// SPDX-License-Identifier: AGPL-3.0-or-later
import type { Meta, StoryObj } from '@storybook/nextjs';
import { expect, fn, userEvent, within } from 'storybook/test';
import { PicturePanel } from './PicturePanel';

const meta: Meta<typeof PicturePanel> = {
  title: 'World/Picture panel',
  component: PicturePanel,
  args: { name: 'Ilsa Marrow', url: null, onSave: fn(async () => null) },
};
export default meta;
type Story = StoryObj<typeof meta>;

export const AddingALink: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Add a picture by link' }));
    await userEvent.type(canvas.getByLabelText('Picture link'), 'https://example.org/ilsa.png');
    await userEvent.click(canvas.getByRole('button', { name: 'Save picture' }));
    await expect(args.onSave).toHaveBeenCalledWith('https://example.org/ilsa.png');
  },
};

export const Linked: Story = {
  args: { url: 'https://example.org/ilsa.png' },
  play: async ({ canvasElement }) => {
    const image = within(canvasElement).getByRole('img', { name: 'Picture of Ilsa Marrow' });
    await expect(image.getAttribute('referrerpolicy')).toBe('no-referrer');
  },
};
