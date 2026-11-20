// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FACTIONS, PLACES } from './fixtures';
import { ParentTree, treeOf } from './ParentTree';

describe('treeOf', () => {
  it('nests each place under its parent, siblings by name', () => {
    const roots = treeOf(PLACES);
    expect(roots.map((node) => node.row.name)).toEqual(['The Coast']);
    expect(roots[0]?.children.map((node) => node.row.name)).toEqual(['Brine', 'Saltmarsh']);
    expect(roots[0]?.children[1]?.children.map((node) => node.row.name)).toEqual(['The Gull']);
  });

  it('puts a place whose parent is missing at the top', () => {
    const orphan = { ...PLACES[2]!, parent_id: 'gone' };
    expect(treeOf([orphan]).map((node) => node.row.name)).toEqual(['The Gull']);
  });
});

describe('ParentTree', () => {
  it('links every place, with its kind', () => {
    render(<ParentTree rows={PLACES} label='Places by where they sit' hrefOf={(place) => `/w/w1/location/${place.id}`} />);
    const nav = screen.getByRole('navigation', { name: 'Places by where they sit' });
    expect(within(nav).getByRole('link', { name: /The Gull/ })).toHaveAttribute('href', '/w/w1/location/l3');
    expect(within(nav).getByRole('link', { name: /Saltmarsh city/ })).toBeInTheDocument();
  });

  it('draws organisations the same way, under their own label', () => {
    render(<ParentTree rows={FACTIONS} label='Organisations by who they answer to' hrefOf={(row) => `/w/w1/faction/${row.id}`} />);
    const nav = screen.getByRole('navigation', { name: 'Organisations by who they answer to' });
    expect(within(nav).getByRole('link', { name: /The Cadet Line family/ })).toHaveAttribute('href', '/w/w1/faction/f2');
  });
});
