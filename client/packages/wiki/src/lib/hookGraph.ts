// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The hook DAG's rule, as the server's (the framework's would_create_dag_cycle in world_narrative's
 * _dependency_no_cycle): an edge parent → child would close a cycle when the child is already an
 * ancestor of the parent, or is the parent itself. Pure, over the owner's existing edges.
 */
export interface HookEdge {
  parentHookId: string;
  childHookId: string;
}

export function wouldCloseCycle(edges: readonly HookEdge[], parentHookId: string, childHookId: string): boolean {
  if (parentHookId === childHookId) return true;
  const parentsOf = new Map<string, string[]>();
  for (const edge of edges) parentsOf.set(edge.childHookId, [...(parentsOf.get(edge.childHookId) ?? []), edge.parentHookId]);
  const seen = new Set([parentHookId]);
  const frontier = [parentHookId];
  while (frontier.length > 0) {
    const node = frontier.pop() as string;
    for (const parent of parentsOf.get(node) ?? []) {
      if (parent === childHookId) return true;
      if (!seen.has(parent)) {
        seen.add(parent);
        frontier.push(parent);
      }
    }
  }
  return false;
}
