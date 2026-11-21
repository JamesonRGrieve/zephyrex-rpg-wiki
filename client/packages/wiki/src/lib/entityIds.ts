// SPDX-License-Identifier: AGPL-3.0-or-later
/** The ids GET /v1/world_entity?ids= names (contract/entity-ids-cases.json), as the server reads them. */
import { LIMITS } from '../contract';

export const MAX_IDS: number = LIMITS.world_entity_ids;

export class EntityIdsError extends Error {}

/** Each id trimmed, blanks dropped, repeats kept once in first order; none, or more than the limit, is refused. */
export function entityIds(values: readonly string[]): string[] {
  const ids = [...new Set(values.map((value) => value.trim()).filter((value) => value !== ''))];
  if (ids.length === 0) throw new EntityIdsError('no ids');
  if (ids.length > MAX_IDS) throw new EntityIdsError(`at most ${MAX_IDS} ids`);
  return ids;
}
