// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { WriteProblem } from './WriteProblem';

describe('WriteProblem', () => {
  it('announces the reason as an alert', () => {
    render(<WriteProblem problem='The world could not be made: Someone else changed it' />);
    expect(screen.getByRole('alert')).toHaveTextContent('Someone else changed it');
  });

  it('shows nothing when there is no problem', () => {
    const { container } = render(<WriteProblem problem={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
