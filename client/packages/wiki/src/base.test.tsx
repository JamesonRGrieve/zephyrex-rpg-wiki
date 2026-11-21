// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';
import { SettingSectionsOf, SettingSectionsProvider, useWikiBase, WikiBaseProvider } from './base';

function Shown(): ReactElement {
  return <p>{useWikiBase()}</p>;
}

describe('the wiki’s base path', () => {
  it('is /w without a provider, and the provider’s base with one slash in front', () => {
    const { rerender } = render(<Shown />);
    expect(screen.getByText('/w')).toBeInTheDocument();
    rerender(
      <WikiBaseProvider base='/wiki/'>
        <Shown />
      </WikiBaseProvider>,
    );
    expect(screen.getByText('/wiki')).toBeInTheDocument();
  });
});

describe('setting sections', () => {
  it("renders the app's sections for a setting, each under its title, and nothing without any", () => {
    const { container, rerender } = render(<SettingSectionsOf settingId='s1' />);
    expect(container).toBeEmptyDOMElement();
    rerender(
      <SettingSectionsProvider sections={[{ id: 'game-systems', title: 'Game systems', render: (id) => <p>{`systems of ${id}`}</p> }]}>
        <SettingSectionsOf settingId='s1' />
      </SettingSectionsProvider>,
    );
    expect(screen.getByRole('heading', { name: 'Game systems' })).toBeInTheDocument();
    expect(screen.getByText('systems of s1')).toBeInTheDocument();
  });
});
