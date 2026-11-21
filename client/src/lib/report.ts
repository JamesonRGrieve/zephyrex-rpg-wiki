// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A session report's body as a Plate value (rpg-ai A24), the same rule as the server's
 * (server/extensions/wiki_shared/Report.py), held to contract/report-body-cases.json. The title is
 * the journal's name and never appears in the body. Plain text becomes one paragraph per
 * blank-line-separated block; mentions close the body with a "Mentioned:" paragraph of mention nodes
 * (typed references, never names alone).
 */
import { checked, type Entry, type EntryElement, type EntryNode } from '~/lib/entry';

export interface NamedMention {
  target_entity_type: string;
  target_entity_id: string;
  name: string;
}

function paragraphs(text: string): Entry {
  return text
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter((block) => block !== '')
    .map((block) => ({ type: 'p', children: [{ text: block }] }));
}

export function reportEntry(body: unknown, mentions: readonly NamedMention[]): Entry {
  const entry: Entry = Array.isArray(body) ? [...checked(body)] : paragraphs(String(body));
  if (mentions.length > 0) {
    const children: EntryNode[] = [{ text: 'Mentioned: ' }];
    mentions.forEach((mention, index) => {
      if (index > 0) children.push({ text: ', ' });
      children.push({
        type: 'mention',
        target_entity_type: mention.target_entity_type,
        target_entity_id: mention.target_entity_id,
        children: [{ text: mention.name }],
      });
    });
    children.push({ text: '' });
    entry.push({ type: 'p', children });
  }
  return entry;
}

/** The mentions an entry holds, in order: every mention node's type and id. */
export function mentionsIn(entry: readonly EntryNode[]): { target_entity_type: string; target_entity_id: string }[] {
  const found: { target_entity_type: string; target_entity_id: string }[] = [];
  const walk = (nodes: readonly EntryNode[]): void => {
    for (const node of nodes) {
      if (!Array.isArray(node.children)) continue;
      const element = node as EntryElement;
      const type = element.target_entity_type;
      const id = element.target_entity_id;
      if (element.type === 'mention' && typeof type === 'string' && typeof id === 'string') {
        found.push({ target_entity_type: type, target_entity_id: id });
      }
      walk(element.children);
    }
  };
  walk(entry);
  return found;
}
