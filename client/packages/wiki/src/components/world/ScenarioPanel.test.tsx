// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ScenarioPanel } from './ScenarioPanel';

describe('ScenarioPanel', () => {
  it('shows nothing for a world that is neither', () => {
    const { container } = render(<ScenarioPanel isScenario={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('starts a playthrough of a scenario, named or not, and says why it failed', async () => {
    const onStart = vi.fn().mockResolvedValueOnce(null).mockResolvedValueOnce('The playthrough could not be started: offline');
    render(<ScenarioPanel isScenario onStart={onStart} />);
    await userEvent.type(screen.getByLabelText('Name of the playthrough'), ' Run 1 ');
    await userEvent.click(screen.getByRole('button', { name: 'Start a playthrough' }));
    expect(onStart).toHaveBeenLastCalledWith('Run 1');
    await userEvent.clear(screen.getByLabelText('Name of the playthrough'));
    await userEvent.click(screen.getByRole('button', { name: 'Start a playthrough' }));
    expect(onStart).toHaveBeenLastCalledWith(null);
    expect(screen.getByRole('alert')).toHaveTextContent('offline');
  });

  it('links a playthrough back to its scenario', () => {
    render(<ScenarioPanel isScenario={false} scenario={{ name: 'The Flicker', href: '/w/s1/about' }} />);
    expect(screen.getByRole('link', { name: 'The Flicker' })).toHaveAttribute('href', '/w/s1/about');
  });
});
