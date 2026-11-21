// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A world's plot state on the client, as the server's rpg_core.plot_state computes it: each hook's
 * state from its requirement (or, without one, all its dependency parents) and what is resolved.
 */
import { type Hook, hookDependencies, hooks } from '~/features/data/records';
import { checkedRequirement, type HookState, hookState, type Requirement } from '~/lib/requirements';

export interface PlotState {
  hooks: Hook[] | undefined;
  error: Error | undefined;
  stateOf: (hook: Hook) => HookState;
  requirementOf: (hook: Hook) => Requirement | null;
  nameOf: (id: string) => string;
  /** When each resolved hook was resolved (ISO), for dispositions and relation influences. */
  resolvedAt: Record<string, string>;
  retry: () => Promise<unknown>;
}

export function usePlot(world: string): PlotState {
  const all = hooks.useList({ campaign_id: world });
  const edges = hookDependencies.useList();
  const rows = all.data;
  const resolvedAt: Record<string, string> = {};
  for (const hook of rows ?? []) if (hook.resolved_at !== null) resolvedAt[hook.id] = hook.resolved_at;
  const requirementOf = (hook: Hook): Requirement | null => {
    if (hook.requires !== null) return checkedRequirement(JSON.parse(hook.requires) as unknown);
    const parents = (edges.data ?? []).filter((edge) => edge.child_hook_id === hook.id).map((edge) => edge.parent_hook_id);
    return parents.length === 0 ? null : { all: parents };
  };
  const names = new Map((rows ?? []).map((hook) => [hook.id, hook.name]));
  return {
    hooks: rows === undefined || edges.data === undefined ? undefined : rows,
    error: all.error ?? edges.error,
    stateOf: (hook) => hookState(requirementOf(hook), Object.keys(resolvedAt), hook.resolved_at !== null),
    requirementOf,
    nameOf: (id) => names.get(id) ?? 'a hook',
    resolvedAt,
    retry: () => Promise.all([all.mutate(), edges.mutate()]),
  };
}
