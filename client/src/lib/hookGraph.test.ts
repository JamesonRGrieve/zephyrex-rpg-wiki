// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM. The hook DAG's cycle rule, the server's own.
import { describe, expect, it } from 'vitest';
import { wouldCloseCycle } from './hookGraph';

const edge = (parentHookId: string, childHookId: string) => ({ parentHookId, childHookId });
const CHAIN = [edge('find', 'reach'), edge('reach', 'slay')];

describe('wouldCloseCycle', () => {
  it('refuses a hook waiting on itself', () => {
    expect(wouldCloseCycle([], 'find', 'find')).toBe(true);
  });

  it('refuses an edge back up the chain, near or far', () => {
    expect(wouldCloseCycle(CHAIN, 'reach', 'find')).toBe(true);
    expect(wouldCloseCycle(CHAIN, 'slay', 'find')).toBe(true);
  });

  it('allows a new branch, a shortcut and a diamond', () => {
    expect(wouldCloseCycle(CHAIN, 'find', 'slay')).toBe(false);
    expect(wouldCloseCycle(CHAIN, 'rumour', 'slay')).toBe(false);
    expect(wouldCloseCycle([...CHAIN, edge('find', 'side')], 'side', 'slay')).toBe(false);
  });
});
