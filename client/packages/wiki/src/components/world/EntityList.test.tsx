// SPDX-License-Identifier: AGPL-3.0-or-later
import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { UNDO_MS } from 'zephyrex/hooks/useToast';
import { LOCATION_KINDS } from '../../contract';
import { EntityList, kindLabel, matching } from './EntityList';
import { PLACES } from './fixtures';

const props = {
  what: 'place',
  plural: 'places',
  kinds: LOCATION_KINDS,
  hrefOf: (row: { id: string }) => `/w/w1/location/${row.id}`,
  onCreate: () => Promise.resolve(true),
  onDelete: vi.fn(),
};

describe('matching', () => {
  it('keeps the rows holding every word, in name or text, case aside', () => {
    expect(matching(PLACES, 'PORT').map((row) => row.name)).toEqual(['Saltmarsh']);
    expect(matching(PLACES, 'inn sign').map((row) => row.name)).toEqual(['The Gull']);
    expect(matching(PLACES, '  ')).toHaveLength(PLACES.length);
  });
});

describe('kindLabel', () => {
  it('reads underscores as spaces', () => {
    expect(kindLabel('body_part')).toBe('body part');
  });
});

describe('EntityList', () => {
  it('lists the rows, each opening its page, read with a space before the kind', () => {
    render(<EntityList {...props} rows={PLACES} />);
    expect(screen.getByRole('link', { name: /^Saltmarsh city/ })).toHaveAttribute('href', '/w/w1/location/l2');
  });

  it('marks a template, so it is never taken for a world fact', () => {
    render(<EntityList {...props} rows={[{ ...PLACES[1]!, is_template: true }, PLACES[3]!]} />);
    expect(screen.getByRole('link', { name: /^Saltmarsh city Template/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^Brine city$/ })).toBeInTheDocument();
  });

  it('finds rows by a search, and says when nothing matches', async () => {
    render(<EntityList {...props} rows={PLACES} />);
    const search = screen.getByRole('searchbox', { name: 'Find places' });
    await userEvent.type(search, 'port');
    expect(screen.getAllByRole('link')).toHaveLength(1);
    await userEvent.clear(search);
    await userEvent.type(search, 'volcano');
    expect(screen.getByText('No places match “volcano”.')).toBeInTheDocument();
  });

  it('shows loading, a load failure with a retry, and a first one to add', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<EntityList {...props} rows={undefined} />);
    expect(screen.getByText('Loading places')).toBeInTheDocument();
    rerender(<EntityList {...props} rows={undefined} error={new Error('offline')} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalled();
    rerender(<EntityList {...props} rows={[]} />);
    expect(screen.getByText('No places here yet. Add the first one above.')).toBeInTheDocument();
  });

  it('adds one with its name and kind', async () => {
    const onCreate = vi.fn().mockResolvedValue(true);
    render(<EntityList {...props} rows={[]} onCreate={onCreate} />);
    await userEvent.type(screen.getByLabelText('New place'), 'Brine');
    await userEvent.selectOptions(screen.getByLabelText('Kind'), 'city');
    await userEvent.click(screen.getByRole('button', { name: 'Add' }));
    expect(onCreate).toHaveBeenCalledWith({ name: 'Brine', kind: 'city' });
    expect(screen.getByLabelText('New place')).toHaveValue('');
  });

  it('deletes only once the undo window has passed', () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const onDelete = vi.fn();
      render(<EntityList {...props} rows={[PLACES[1]!]} onDelete={onDelete} />);
      fireEvent.click(screen.getByRole('button', { name: 'Delete Saltmarsh' }));
      expect(screen.queryByRole('link', { name: /Saltmarsh/ })).not.toBeInTheDocument();
      expect(screen.queryByText(/No places here yet/)).not.toBeInTheDocument();
      expect(onDelete).not.toHaveBeenCalled();
      act(() => {
        vi.advanceTimersByTime(UNDO_MS);
      });
      expect(onDelete).toHaveBeenCalledWith(PLACES[1]);
    } finally {
      vi.useRealTimers();
    }
  });
});
