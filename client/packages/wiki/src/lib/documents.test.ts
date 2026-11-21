// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/document-cases.json';
import { orderedDocuments } from './documents';

describe('orderedDocuments (contract/document-cases.json)', () => {
  it.each(cases.cases)('$name', (one) => {
    const documents = orderedDocuments(one.records);
    expect(documents.map((document) => document.id)).toEqual(one.ids);
    if ('texts' in one) expect(documents.map((document) => document.text)).toEqual(one.texts);
  });
});
