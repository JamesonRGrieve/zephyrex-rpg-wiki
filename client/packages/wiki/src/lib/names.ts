// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * S4c: a record's aliases and keywords, and a person's AI voice, checked and normalised as the
 * server's wiki_shared/Names.py does; both are held to contract/name-list-cases.json. Both are
 * kept as JSON text, as an entry is.
 */
import { DEPTH_PROMPT_ROLES, LIMITS, VOICE_DEFAULTS, VOICE_PARTS } from '../contract';

/** A Character's Note (SillyTavern's depth prompt): inserted `depth` messages up, as `role`. */
export interface DepthPrompt {
  prompt: string;
  depth: number;
  role: string;
}

export interface Voice {
  personality: string;
  speech: string;
  first_message: string;
  examples: string[];
  /** Parity: SillyTavern's card fields. */
  system_prompt: string;
  post_history_instructions: string;
  depth_prompt: DepthPrompt | null;
  talkativeness: number;
  across_chats: boolean;
}

const PARTS_RULE = `A voice's parts are ${VOICE_PARTS.join(', ')}`;
const DEPTH_RULE = `A voice's depth_prompt is a prompt, a depth from 0 to ${LIMITS.depth_prompt_depth} and a role (${DEPTH_PROMPT_ROLES.join(', ')})`;
type TextPart = 'personality' | 'speech' | 'first_message' | 'system_prompt' | 'post_history_instructions';

function depthPrompt(value: unknown): DepthPrompt | null {
  if (value === undefined || value === null) return null;
  if (!isRecord(value) || Object.keys(value).some((key) => !['prompt', 'depth', 'role'].includes(key))) throw new Error(DEPTH_RULE);
  const prompt = value.prompt ?? '';
  const depth = value.depth ?? VOICE_DEFAULTS.depth_prompt_depth;
  const role = value.role || VOICE_DEFAULTS.depth_prompt_role;
  if (typeof prompt !== 'string' || prompt.length > LIMITS.voice_characters || typeof depth !== 'number' || !Number.isInteger(depth))
    throw new Error(DEPTH_RULE);
  if (depth < 0 || depth > LIMITS.depth_prompt_depth || typeof role !== 'string' || !DEPTH_PROMPT_ROLES.includes(role)) throw new Error(DEPTH_RULE);
  return prompt.trim() === '' ? null : { prompt: prompt.trim(), depth, role };
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
  if (!isRecord(given) || Object.keys(given).some((key) => !VOICE_PARTS.includes(key))) throw new Error(PARTS_RULE);
  const text = (part: TextPart): string => {
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
  const talkativeness = given.talkativeness ?? VOICE_DEFAULTS.talkativeness;
  if (typeof talkativeness !== 'number' || Number.isNaN(talkativeness) || talkativeness < 0 || talkativeness > 1)
    throw new Error("A voice's talkativeness is from 0 to 1");
  const acrossChats = given.across_chats ?? VOICE_DEFAULTS.across_chats;
  if (typeof acrossChats !== 'boolean') throw new Error("A voice's across_chats is yes or no");
  return {
    personality: text('personality'),
    speech: text('speech'),
    first_message: text('first_message'),
    examples: kept,
    system_prompt: text('system_prompt'),
    post_history_instructions: text('post_history_instructions'),
    depth_prompt: depthPrompt(given.depth_prompt),
    talkativeness,
    across_chats: acrossChats,
  };
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
