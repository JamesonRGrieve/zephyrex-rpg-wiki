// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Landing } from './Landing';

describe('Landing', () => {
  it('has one h1, the planned features, the comparison and the FAQ', () => {
    render(<Landing />);
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('region', { name: 'What it will do' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Kanka and World Anvil' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Questions' })).toBeInTheDocument();
  });

  it('says nothing is live yet, and points the way in at the plan', () => {
    render(<Landing />);
    expect(screen.getByText(/nothing below is live yet/)).toBeInTheDocument();
    for (const link of screen.getAllByRole('link', { name: 'See what is planned' })) {
      expect(link).toHaveAttribute('href', '#planned');
    }
  });
});
