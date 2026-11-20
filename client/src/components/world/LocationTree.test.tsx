// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PLACES } from './fixtures';
import { LocationTree, treeOf } from './LocationTree';

describe('treeOf', () => {
  it('nests each place under its parent, siblings by name', () => {
    const roots = treeOf(PLACES);
    expect(roots.map((node) => node.place.name)).toEqual(['The Coast']);
    expect(roots[0]?.children.map((node) => node.place.name)).toEqual(['Brine', 'Saltmarsh']);
    expect(roots[0]?.children[1]?.children.map((node) => node.place.name)).toEqual(['The Gull']);
  });

  it('puts a place whose parent is missing at the top', () => {
    const orphan = { ...PLACES[2]!, parent_id: 'gone' };
    expect(treeOf([orphan]).map((node) => node.place.name)).toEqual(['The Gull']);
  });
});

describe('LocationTree', () => {
  it('links every place, with its kind', () => {
    render(<LocationTree places={PLACES} hrefOf={(place) => `/w/w1/location/${place.id}`} />);
    const nav = screen.getByRole('navigation', { name: 'Places by where they sit' });
    expect(within(nav).getByRole('link', { name: /The Gull/ })).toHaveAttribute('href', '/w/w1/location/l3');
    expect(within(nav).getByRole('link', { name: /Saltmarsh city/ })).toBeInTheDocument();
  });
});
