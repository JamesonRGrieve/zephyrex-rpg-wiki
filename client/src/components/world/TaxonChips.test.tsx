// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { TaxonChips } from './TaxonChips';

const chip = (id: string, name: string, kind: string, colour: string | null = null) => ({ id, name, kind, colour, href: `/w/salt/taxonomy?taxon=${id}` });

describe('TaxonChips', () => {
  it('shows the status and each taxon, linked, naming kinds other than tag', () => {
    render(<TaxonChips status={chip('s1', 'Alive', 'entity_status', '#32a852')} taxa={[chip('t1', 'Nobility', 'tag'), chip('t2', 'Elf', 'race')]} />);
    expect(screen.getByText('Status:')).toBeInTheDocument();
    const tags = within(screen.getByRole('list', { name: 'Tags' }));
    expect(tags.getByRole('link', { name: 'Nobility' })).toHaveAttribute('href', '/w/salt/taxonomy?taxon=t1');
    expect(tags.getByRole('link', { name: 'Elf race' })).toBeInTheDocument();
  });

  it('says so when there is nothing', () => {
    render(<TaxonChips status={null} taxa={[]} />);
    expect(screen.getByText('No tags or status yet.')).toBeInTheDocument();
  });

  it('shows loading, then a load failure with a retry', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<TaxonChips status={undefined} taxa={[]} />);
    expect(screen.getByText('Loading the tags')).toBeInTheDocument();
    rerender(<TaxonChips status={undefined} taxa={undefined} error={new Error('offline')} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
  });
});
