// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A campaign's provenance (contract/provenance-cases.json), as the server's wiki_shared/Provenance.py
 * reads it: homebrew, official (as published) or adapted (from a published one), and its source
 * (title, publisher, product or page). What isn't given is homebrew with no source.
 */
import { LIMITS, PROVENANCES } from '../contract';

export const HOMEBREW = PROVENANCES[0] ?? 'homebrew';

// A type, not an interface: written into a record's columns, it must read as a plain record.
export type Provenance = {
  provenance: string;
  source: string | null;
};

export class ProvenanceError extends Error {}

export function checkedSource(value: unknown): string | null {
  if (value === undefined || value === null) return null;
  if (typeof value !== 'string') throw new ProvenanceError('A source is text');
  const text = value.trim();
  if (text.length > LIMITS.source_characters) throw new ProvenanceError(`A source has at most ${LIMITS.source_characters} characters`);
  return text === '' ? null : text;
}

export function provenance(value: { provenance?: unknown; source?: unknown }): Provenance {
  const kind = value.provenance === undefined || value.provenance === null || value.provenance === '' ? HOMEBREW : value.provenance;
  if (typeof kind !== 'string' || !PROVENANCES.includes(kind)) throw new ProvenanceError(`provenance is one of ${PROVENANCES.join(', ')}`);
  const source = checkedSource(value.source);
  if (kind === HOMEBREW && source !== null) throw new ProvenanceError('Homebrew has no source');
  return { provenance: kind, source };
}
