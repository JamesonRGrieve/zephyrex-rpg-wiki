// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM. A session report's body, held to the cases the server is held to
// (contract/report-body-cases.json).
import { describe, expect, it } from 'vitest';
import cases from '../../../contract/report-body-cases.json';
import { mentionsIn, reportEntry } from './report';

describe('reportEntry', () => {
  it.each(cases.cases.map((one) => [one.name, one] as const))('%s', (_name, one) => {
    expect(reportEntry(one.body, one.mentions)).toEqual(one.entry);
  });
});

describe('mentionsIn', () => {
  it('finds each mention node, in order', () => {
    const withMentions = cases.cases.find((one) => one.mentions.length > 0);
    expect(mentionsIn(reportEntry(withMentions?.body, withMentions?.mentions ?? []))).toEqual(
      (withMentions?.mentions ?? []).map(({ target_entity_type, target_entity_id }) => ({ target_entity_type, target_entity_id })),
    );
  });
});
