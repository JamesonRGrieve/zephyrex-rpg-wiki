// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A property kit's keys (S4b, W4), checked and normalised as the server's
 * wiki_shared/Properties.py does; both are held to contract/property-kit-cases.json.
 */
import { LIMITS, PROPERTY_VALUE_TYPES } from '~/contract';

export interface KitProperty {
  key: string;
  value_type: string;
  default: string | null;
  is_private: boolean;
  ordinal: number;
}

/** Why a kit's properties are refused, in words for the person who wrote them. */
export class KitError extends Error {}

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);

/** A default as the record's value is kept: text (a number or a switch written as text), or none. */
function defaultOf(value: unknown): string | null {
  if (value === undefined || value === null) return null;
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') return String(value);
  if (typeof value !== 'string') throw new KitError('A default is text, a number or true/false');
  if (value.length > LIMITS.property_value_characters) throw new KitError(`A default has at most ${LIMITS.property_value_characters} characters`);
  return value;
}

/** A kit's properties, normalised: each key trimmed and named once, its type from the contract, its place its position when not given. */
export function checkedKit(properties: unknown): KitProperty[] {
  if (!Array.isArray(properties)) throw new KitError("A kit's properties are a list");
  if (properties.length > LIMITS.properties_per_record) throw new KitError(`A kit has at most ${LIMITS.properties_per_record} properties`);
  const seen = new Set<string>();
  return properties.map((item: unknown, place) => {
    if (!isRecord(item)) throw new KitError('Each property is an object with a key');
    const key = typeof item.key === 'string' ? item.key.trim() : '';
    if (key === '') throw new KitError('Each property has a key');
    if (key.length > LIMITS.property_key_characters) throw new KitError(`A key has at most ${LIMITS.property_key_characters} characters`);
    if (seen.has(key)) throw new KitError(`The key '${key}' is in the kit twice`);
    seen.add(key);
    const valueType = typeof item.value_type === 'string' && item.value_type !== '' ? item.value_type : 'text';
    if (!PROPERTY_VALUE_TYPES.includes(valueType)) throw new KitError(`A value type is one of: ${PROPERTY_VALUE_TYPES.join(', ')}`);
    const ordinal = item.ordinal ?? place;
    if (typeof ordinal !== 'number' || !Number.isInteger(ordinal) || ordinal < 0)
      throw new KitError("A property's place is a whole number of zero or more");
    const isPrivate = item.is_private ?? false;
    if (typeof isPrivate !== 'boolean') throw new KitError('is_private is true or false');
    return { key, value_type: valueType, default: defaultOf(item.default), is_private: isPrivate, ordinal };
  });
}
