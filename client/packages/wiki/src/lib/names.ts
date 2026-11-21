// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * S4c: a record's aliases and keywords, and a person's AI voice, checked and normalised as the
 * server's wiki_shared/Names.py does; both are held to contract/name-list-cases.json. Both are
 * kept as JSON text, as an entry is.
 */
import { LIMITS, VOICE_PARTS } from '../contract';

export interface Voice {
  personality: string;
  speech: string;
  first_message: string;
  examples: string[];
}

const loaded = (value: unknown): unknown => (typeof value === 'string' ? JSON.parse(value) : value);

/** A list of names: each trimmed, blanks dropped, each once (case aside), in order. */
export function names(value: unknown): string[] {
  const list = loaded(value);
  if (!Array.isArray(list) || list.some((one) => typeof one !== 'string')) throw new Error('A list of names is a list of text');
  const seen = new Set<string>();
  const kept: string[] = [];
  for (const one of list as string[]) {
    const name = one.trim();
    if (name === '' || seen.has(name.toLowerCase())) continue;
    if (name.length > LIMITS.name_characters) throw new Error(`A name has at most ${LIMITS.name_characters} characters`);
    seen.add(name.toLowerCase());
    kept.push(name);
  }
  if (kept.length > LIMITS.names_per_list) throw new Error(`A list holds at most ${LIMITS.names_per_list} names`);
  return kept;
}

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);

/** A person's AI voice, every part present (empty when not given) and trimmed, each example once. */
export function voice(value: unknown): Voice {
  const given = loaded(value);
  if (!isRecord(given) || Object.keys(given).some((key) => !(VOICE_PARTS as readonly string[]).includes(key)))
    throw new Error('A voice is personality, speech, first_message and examples');
  const text = (part: 'personality' | 'speech' | 'first_message'): string => {
    const raw = given[part] ?? '';
    if (typeof raw !== 'string') throw new Error(`A voice's ${part} is text`);
    if (raw.length > LIMITS.voice_characters) throw new Error(`A voice's ${part} has at most ${LIMITS.voice_characters} characters`);
    return raw.trim();
  };
  const examples = given.examples ?? [];
  if (!Array.isArray(examples) || examples.some((one) => typeof one !== 'string')) throw new Error("A voice's examples are a list of text");
  const kept = [...new Set((examples as string[]).map((one) => one.trim()).filter((one) => one !== ''))];
  if (kept.length > LIMITS.voice_examples || kept.some((one) => one.length > LIMITS.voice_characters))
    throw new Error(`A voice has at most ${LIMITS.voice_examples} examples of at most ${LIMITS.voice_characters} characters`);
  return { personality: text('personality'), speech: text('speech'), first_message: text('first_message'), examples: kept };
}

/** A stored list read back; an unreadable one is empty. */
export function storedNames(text: string | null): string[] {
  if (text === null || text === '') return [];
  try {
    const value: unknown = JSON.parse(text);
    return Array.isArray(value) ? value.filter((one): one is string => typeof one === 'string') : [];
  } catch {
    return [];
  }
}

/** A stored voice read back; none when there is none or it is unreadable. */
export function storedVoice(text: string | null): Voice | null {
  if (text === null || text === '') return null;
  try {
    return voice(JSON.parse(text));
  } catch {
    return null;
  }
}
