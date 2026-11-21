// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PicturePanel } from './PicturePanel';

const LINK = 'https://static.wikia.nocookie.net/warhammer40k/images/a/a1/Inquisitor.jpg';

describe('PicturePanel', () => {
  it('shows a linked picture with no referrer, and nothing to a reader without one', () => {
    const { rerender } = render(<PicturePanel name='Ilsa' url={LINK} />);
    const image = screen.getByRole('img', { name: 'Picture of Ilsa' });
    expect([image.getAttribute('src'), image.getAttribute('referrerpolicy')]).toEqual([LINK, 'no-referrer']);
    rerender(<PicturePanel name='Ilsa' url={null} />);
    expect(screen.queryByRole('region', { name: 'Picture' })).not.toBeInTheDocument();
  });

  it('saves a pasted link trimmed, takes one off, and keeps the form with the reason on failure', async () => {
    const onSave = vi.fn().mockResolvedValueOnce('The picture could not be saved: not https').mockResolvedValue(null);
    const { rerender } = render(<PicturePanel name='Ilsa' url={null} onSave={onSave} />);
    await userEvent.click(screen.getByRole('button', { name: 'Add a picture by link' }));
    await userEvent.type(screen.getByLabelText('Picture link'), `  ${LINK} `);
    await userEvent.click(screen.getByRole('button', { name: 'Save picture' }));
    expect(onSave).toHaveBeenLastCalledWith(LINK);
    expect(screen.getByRole('alert')).toHaveTextContent('not https');
    await userEvent.click(screen.getByRole('button', { name: 'Save picture' }));
    expect(screen.queryByLabelText('Picture link')).not.toBeInTheDocument();
    rerender(<PicturePanel name='Ilsa' url={LINK} onSave={onSave} />);
    await userEvent.click(screen.getByRole('button', { name: 'Change picture' }));
    await userEvent.click(screen.getByRole('button', { name: 'Take it off' }));
    expect(onSave).toHaveBeenLastCalledWith(null);
  });
});
