// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * S4d: a record's lorebook activation (SillyTavern World Info's fields, for rpg-ai's activation),
 * checked and filled with the contract's defaults as the server's wiki_shared/Lore.py does; both are
 * held to contract/lore-cases.json. Kept as JSON text, as an entry is.
 */
import { LORE_DEFAULTS, LORE_LOGIC, LORE_POSITIONS } from '../contract';
import { names } from './names';

export interface Lore {
  always_active: boolean;
  order: number;
  position: string;
  depth: number;
  probability: number;
  selective_logic: string;
  secondary_keys: string[];
  sticky: number;
  cooldown: number;
  delay: number;
  group: string;
  group_weight: number;
}

const MAX_GROUP = 200;
type Whole = 'order' | 'depth' | 'probability' | 'sticky' | 'cooldown' | 'delay' | 'group_weight';

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);

function whole(name: Whole, value: unknown): number {
  if (typeof value !== 'number' || !Number.isInteger(value)) throw new Error(`${name} is a whole number`);
  if (name === 'probability' && (value < 0 || value > 100)) throw new Error('probability is a whole number from 0 to 100');
  if ((name === 'depth' || name === 'sticky' || name === 'cooldown' || name === 'delay') && value < 0)
    throw new Error(`${name} is a whole number of zero or more`);
  if (name === 'group_weight' && value < 1) throw new Error('group_weight is a whole number of one or more');
  return value;
}

/** A lore block, every field present (the contract's default when not given). */
export function lore(value: unknown): Lore {
  const given: unknown = typeof value === 'string' ? JSON.parse(value) : value;
  if (!isRecord(given) || Object.keys(given).some((key) => !(key in LORE_DEFAULTS)))
    throw new Error("A lore block is an object of SillyTavern's activation fields");
  const merged: Record<string, unknown> = { ...LORE_DEFAULTS, ...given };
  if (typeof merged.always_active !== 'boolean') throw new Error('always_active is true or false');
  if (typeof merged.position !== 'string' || !LORE_POSITIONS.includes(merged.position))
    throw new Error(`A lore position is one of: ${LORE_POSITIONS.join(', ')}`);
  if (typeof merged.selective_logic !== 'string' || !LORE_LOGIC.includes(merged.selective_logic))
    throw new Error(`Lore logic is one of: ${LORE_LOGIC.join(', ')}`);
  const group = merged.group;
  if (typeof group !== 'string' || group.trim().length > MAX_GROUP) throw new Error(`A lore group is a name of at most ${MAX_GROUP} characters`);
  return {
    always_active: merged.always_active,
    order: whole('order', merged.order),
    position: merged.position,
    depth: whole('depth', merged.depth),
    probability: whole('probability', merged.probability),
    selective_logic: merged.selective_logic,
    secondary_keys: names(merged.secondary_keys),
    sticky: whole('sticky', merged.sticky),
    cooldown: whole('cooldown', merged.cooldown),
    delay: whole('delay', merged.delay),
    group: group.trim(),
    group_weight: whole('group_weight', merged.group_weight),
  };
}

/** A stored lore block read back; none when there is none or it is unreadable. */
export function storedLore(text: string | null): Lore | null {
  if (text === null || text === '') return null;
  try {
    return lore(JSON.parse(text));
  } catch {
    return null;
  }
}
