// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A SillyTavern character card as a wiki person, as the server's wiki_shared/Cards.py
 * (contract/card-cases.json). Fields by the spec's names or rpg-ai's (first_message, example_messages).
 */
export const CHARACTERS = 'Characters';

type Card = Record<string, unknown>;

export function cardData(card: Card): Card {
  const data: Card = { ...card };
  if (!('first_mes' in data) && 'first_message' in data) data.first_mes = data.first_message;
  if (!('mes_example' in data) && 'example_messages' in data) data.mes_example = data.example_messages;
  return data;
}

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

function talkativeness(value: unknown): number | null {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null;
  const number = Number(value);
  return Number.isNaN(number) ? null : number;
}

export function cardVoice(name: string, data: Card): Record<string, unknown> {
  const filled = (value: unknown): string =>
    text(value).replaceAll('{{char}}', name).replaceAll('{{user}}', 'User').replaceAll('<USER>', 'User').replaceAll('<BOT>', name).trim();
  const examples = text(data.mes_example).split('<START>').map(filled).filter((one) => one !== '');
  const extensions = (data.extensions ?? {}) as Record<string, unknown>;
  const note = (extensions.depth_prompt ?? {}) as Record<string, unknown>;
  const given: Record<string, unknown> = {
    personality: filled(data.personality),
    speech: '',
    first_message: filled(data.first_mes),
    examples: [...new Set(examples)],
    system_prompt: filled(data.system_prompt),
    post_history_instructions: filled(data.post_history_instructions),
  };
  if (text(note.prompt).trim() !== '') given.depth_prompt = { prompt: filled(note.prompt), depth: Number(note.depth ?? 4), role: text(note.role) || 'system' };
  const talk = talkativeness(extensions.talkativeness);
  if (talk !== null) given.talkativeness = talk;
  return given;
}

export function cardMarkdown(data: Card): string {
  const description = text(data.description).trim();
  const scenario = text(data.scenario).trim();
  return description + (scenario ? `\n\n## Scenario\n\n${scenario}` : '');
}

const list = (value: unknown): string[] => (Array.isArray(value) ? value.map((one) => text(one).trim()).filter((one) => one !== '') : []);
export const cardGreetings = (data: Card): string[] => list(data.alternate_greetings);
export const cardTags = (data: Card): string[] => [...new Set(list(data.tags))];

export function cardAvatar(card: Card): string | null {
  const avatar = text(card.avatar).trim();
  if (avatar.startsWith('data:')) throw new Error('Upload the avatar first and give an https link');
  return avatar === '' ? null : avatar;
}
