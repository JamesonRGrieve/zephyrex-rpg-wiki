// SPDX-License-Identifier: AGPL-3.0-or-later
// @vitest-environment node
// Pure logic: no DOM. Held to the cases the server is held to (contract/requirement-cases.json).
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/requirement-cases.json';
import { checkedRequirement, describeRequirement, hookState, leavesOf, type Requirement, RequirementError } from './requirements';

describe('hookState', () => {
  it.each(cases.cases.map((one) => [one.name, one] as const))('%s', (_name, one) => {
    const requires = one.requires === null ? null : checkedRequirement(one.requires);
    expect(hookState(requires, one.resolved, one.self_resolved)).toBe(one.state);
  });
});

describe('leavesOf', () => {
  it.each(cases.leaves.map((one) => [one] as const))('names each hook once, in order', (one) => {
    expect(leavesOf(one.requires as Requirement)).toEqual(one.hooks);
  });
});

describe('checkedRequirement', () => {
  it.each(cases.invalid.map((one) => [one.name, one] as const))('refuses %s', (_name, one) => {
    expect(() => checkedRequirement(one.requires)).toThrow(RequirementError);
  });
});

describe('describeRequirement', () => {
  const names: Record<string, string> = { A: 'Arrive', N: 'Discover the null' };
  const nameOf = (id: string) => names[id] ?? id;
  it('reads a nested requirement in words, hooks by name', () => {
    const node = checkedRequirement({ all: ['A', { any: [{ char: { skill: ['psyniscience', 'forbidden-lore'] } }, 'N'] }] });
    expect(describeRequirement(node, nameOf)).toBe('Arrive and (a check: skill psyniscience or forbidden-lore or Discover the null)');
  });
  it('names a check everyone must pass, and the empty cases', () => {
    expect(describeRequirement(checkedRequirement({ char: { homeworld: 'voidborn' }, who: 'all' }), nameOf)).toBe('a check for everyone: homeworld voidborn');
    expect(describeRequirement(checkedRequirement({ all: [] }), nameOf)).toBe('nothing');
  });
});
