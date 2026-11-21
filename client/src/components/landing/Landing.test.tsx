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

  it('says what is live and leads into the app', () => {
    render(<Landing />);
    expect(screen.getByText(/are here now; the rest is being built/)).toBeInTheDocument();
    for (const link of screen.getAllByRole('link', { name: 'Open your settings' })) {
      expect(link).toHaveAttribute('href', '/w');
    }
    // The header's nav renders twice (the bar and the phone menu): every copy points at the plan.
    for (const link of screen.getAllByRole('link', { name: 'What is planned' })) {
      expect(link).toHaveAttribute('href', '#planned');
    }
  });
});
