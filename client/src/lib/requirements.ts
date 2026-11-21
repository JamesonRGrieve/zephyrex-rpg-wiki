// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A hook's requirement and state (W57, from dh-campaign's tracker), the same rule as the server's
 * (server/extensions/wiki_shared/Requirements.py), held to contract/requirement-cases.json.
 *
 * A requirement is a hook id, `{ all: [...] }`, `{ any: [...] }` or a game-system check
 * `{ char: { dimension: value | [values] }, who?: 'any' | 'all' }`, which VTT's rpg_systems
 * evaluates; the wiki only says a check is needed.
 */
import { LIMITS } from '~/contract';

export type Requirement = string | { all: Requirement[] } | { any: Requirement[] } | { char: Record<string, string | string[]>; who?: 'any' | 'all' };
export type HookState = 'resolved' | 'available' | 'blocked' | 'needs_check';
type Value = 'met' | 'unmet' | 'check';

export class RequirementError extends Error {}

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);

/** `node` when it's a well-formed requirement; RequirementError otherwise. */
export function checkedRequirement(node: unknown, depth = 0): Requirement {
  if (depth > LIMITS.requirement_depth) throw new RequirementError(`A requirement nests at most ${LIMITS.requirement_depth} deep`);
  if (typeof node === 'string') {
    if (node === '') throw new RequirementError('A requirement names a hook');
    return node;
  }
  if (!isRecord(node)) throw new RequirementError('A requirement is a hook, all, any or char');
  const keys = Object.keys(node).filter((key) => key !== 'who');
  const key = keys[0];
  if (keys.length !== 1 || key === undefined || !['all', 'any', 'char'].includes(key))
    throw new RequirementError('A requirement has exactly one of all, any or char');
  if (key === 'all' || key === 'any') {
    const children = node[key];
    if ('who' in node || !Array.isArray(children)) throw new RequirementError(`${key} is a list of requirements`);
    for (const child of children) checkedRequirement(child, depth + 1);
    return node as Requirement;
  }
  const check = node.char;
  if (!isRecord(check) || Object.keys(check).length === 0) throw new RequirementError('char names at least one dimension');
  for (const value of Object.values(check)) {
    const values = Array.isArray(value) ? value : [value];
    if (values.length === 0 || !values.every((item) => typeof item === 'string' && item !== ''))
      throw new RequirementError('A char dimension’s value is text, or a list of text');
  }
  if (!['any', 'all', undefined].includes(node.who as string | undefined)) throw new RequirementError('who is any or all');
  return node as Requirement;
}

/** The hooks a requirement names, in order, each once. */
export function leavesOf(node: Requirement): string[] {
  const found: string[] = [];
  const walk = (at: Requirement): void => {
    if (typeof at === 'string') {
      if (!found.includes(at)) found.push(at);
    } else if ('all' in at) at.all.forEach(walk);
    else if ('any' in at) at.any.forEach(walk);
  };
  walk(node);
  return found;
}

function valueOf(node: Requirement, done: ReadonlySet<string>): Value {
  if (typeof node === 'string') return done.has(node) ? 'met' : 'unmet';
  if ('char' in node) return 'check';
  if ('all' in node) {
    const children = node.all.map((child) => valueOf(child, done));
    return children.includes('unmet') ? 'unmet' : children.includes('check') ? 'check' : 'met';
  }
  const children = node.any.map((child) => valueOf(child, done));
  return children.includes('met') ? 'met' : children.includes('check') ? 'check' : 'unmet';
}

/** Resolved; else available, needs_check or blocked, from the requirement (none: available). */
export function hookState(requires: Requirement | null, resolved: Iterable<string>, selfResolved: boolean): HookState {
  if (selfResolved) return 'resolved';
  if (requires === null) return 'available';
  const value = valueOf(requires, new Set(resolved));
  return value === 'met' ? 'available' : value === 'check' ? 'needs_check' : 'blocked';
}

/** A requirement in words, hooks by name (`nameOf`), for the GM: "Arrive and (Find the map or a check: skill psyniscience)". */
export function describeRequirement(node: Requirement, nameOf: (id: string) => string): string {
  const words = (at: Requirement, nested: boolean): string => {
    if (typeof at === 'string') return nameOf(at);
    if ('char' in at) {
      const dims = Object.entries(at.char).map(([dim, value]) => `${dim.replaceAll('-', ' ')} ${(Array.isArray(value) ? value : [value]).join(' or ')}`);
      return `${at.who === 'all' ? 'a check for everyone' : 'a check'}: ${dims.join(', ')}`;
    }
    const list = 'all' in at ? at.all : at.any;
    if (list.length === 0) return 'all' in at ? 'nothing' : 'never';
    const joined = list.map((child) => words(child, true)).join('all' in at ? ' and ' : ' or ');
    return nested && list.length > 1 ? `(${joined})` : joined;
  };
  return words(node, false);
}
