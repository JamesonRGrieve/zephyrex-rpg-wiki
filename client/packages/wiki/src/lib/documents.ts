// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A campaign's documents (contract/document-cases.json), as the server's wiki_shared/Documents.py
 * orders them: each record with text, journals first, then document_kinds' order, by name.
 */
import { DOCUMENT_KINDS } from '../contract';

export interface DocumentRecord {
  id: string;
  kind: string;
  name: string;
  text: string | null;
}

export function orderedDocuments<T extends DocumentRecord>(records: readonly T[]): (T & { text: string })[] {
  const rank = new Map(DOCUMENT_KINDS.map((kind, index) => [kind, index]));
  return records
    .map((record) => ({ ...record, text: (record.text ?? '').trim() }))
    .filter((record) => record.text !== '')
    .sort(
      (one, two) =>
        (rank.get(one.kind) ?? rank.size) - (rank.get(two.kind) ?? rank.size) ||
        one.name.toLowerCase().localeCompare(two.name.toLowerCase()) ||
        one.id.localeCompare(two.id),
    );
}
