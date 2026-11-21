// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';
import { useWikiBase, WikiBaseProvider } from './base';

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
