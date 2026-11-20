// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Unavailable } from './Unavailable';

describe('Unavailable', () => {
  it('says what this server does not keep', () => {
    render(<Unavailable what='worlds' />);
    expect(screen.getByText('This server doesn’t keep worlds.')).toBeInTheDocument();
  });
});
