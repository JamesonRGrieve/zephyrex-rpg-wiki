// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A record's entry: a Plate (Slate) value, stored as JSON text, with a plain-text copy kept as the
 * record's description for search (decision 16; operator, 2026-11-20). The same rule as the
 * server's (server/extensions/wiki_shared/Entry.py), held to contract/entry-text-cases.json on
 * both sides: an element with a text leaf among its children is one line (inline elements in it
 * give their text); any other element is a container whose children are read in turn.
 */
import { LIMITS } from '../contract';

export interface EntryLeaf {
  text: string;
  [mark: string]: unknown;
}
export interface EntryElement {
  type?: string;
  children: EntryNode[];
  [attribute: string]: unknown;
}
export type EntryNode = EntryElement | EntryLeaf;
export type Entry = EntryNode[];

/** Thrown for an entry out of shape; the lite routes answer it as a 422. */
export class EntryError extends Error {}

function isLeaf(node: unknown): node is EntryLeaf {
  return typeof node === 'object' && node !== null && 'text' in node && !('children' in node);
}

function check(node: unknown, depth: number): void {
  if (depth > LIMITS.entry_depth) throw new EntryError(`An entry nests at most ${LIMITS.entry_depth} levels`);
  if (isLeaf(node)) {
    if (typeof node.text !== 'string') throw new EntryError('A text leaf’s text must be a string');
    return;
  }
  const children = typeof node === 'object' && node !== null ? Reflect.get(node, 'children') : undefined;
  if (!Array.isArray(children)) throw new EntryError('Every node in an entry is an element with children or a text leaf');
  for (const child of children) check(child, depth + 1);
}

/** The entry as a list of nodes, or an EntryError saying what is wrong with it. */
export function checked(value: unknown): Entry {
  if (!Array.isArray(value)) throw new EntryError('An entry is a list of block elements');
  for (const node of value) check(node, 1);
  return value as Entry;
}

function textOf(node: EntryNode): string {
  return isLeaf(node) ? node.text : node.children.map(textOf).join('');
}

function linesOf(nodes: readonly EntryNode[]): string[] {
  const lines: string[] = [];
  for (const node of nodes) {
    if (isLeaf(node)) continue;
    if (node.children.some(isLeaf)) lines.push(textOf(node));
    else lines.push(...linesOf(node.children));
  }
  return lines;
}

/** The entry's plain-text copy: each line's text, joined by newlines. */
export function plainText(entry: unknown): string {
  return linesOf(checked(entry)).join('\n');
}

/** An entry as sent (its JSON text, or the value itself) → its stored JSON text and plain text. */
export function parseEntry(raw: unknown): { stored: string; text: string } {
  let value = raw;
  if (typeof raw === 'string') {
    try {
      value = JSON.parse(raw) as unknown;
    } catch {
      throw new EntryError('An entry is a list of block elements');
    }
  }
  const stored = JSON.stringify(checked(value));
  if (new TextEncoder().encode(stored).length > LIMITS.entry_bytes) {
    throw new EntryError(`An entry holds at most ${LIMITS.entry_bytes} bytes`);
  }
  return { stored, text: plainText(value) };
}
