// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EntityPage, linesOf } from './EntityPage';
import { ENTRY } from './fixtures';

describe('linesOf', () => {
  it('reads the entry, else the stored plain text, else nothing', () => {
    expect(linesOf(ENTRY, 'stale')).toEqual(['History', 'Founded by smugglers.']);
    expect(linesOf('{broken', 'A port city.')).toEqual(['A port city.']);
    expect(linesOf(null, null)).toEqual([]);
  });
});

describe('EntityPage', () => {
  it('shows the kind, where it sits, and the entry', () => {
    render(
      <EntityPage kind='body_part' entry={ENTRY} description={null} where={{ label: 'In', name: 'Saltmarsh', href: '/w/w1/location/l2' }} />,
    );
    expect(screen.getByText('body part')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Saltmarsh' })).toHaveAttribute('href', '/w/w1/location/l2');
    expect(screen.getByText('Founded by smugglers.')).toBeInTheDocument();
  });

  it('keeps repeated lines, and says when nothing is written', () => {
    const twice = JSON.stringify([
      { type: 'p', children: [{ text: 'Again.' }] },
      { type: 'p', children: [{ text: 'Again.' }] },
    ]);
    const { rerender } = render(<EntityPage kind={null} entry={twice} description={null} />);
    expect(screen.getAllByText('Again.')).toHaveLength(2);
    rerender(<EntityPage kind={null} entry={null} description='' />);
    expect(screen.getByText('Nothing written here yet.')).toBeInTheDocument();
  });
});
