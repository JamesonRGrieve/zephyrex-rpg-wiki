// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/card-cases.json';
import { cardAvatar, cardData, cardGreetings, cardMarkdown, cardTags, cardVoice } from './cards';

describe('a card as a person (contract/card-cases.json)', () => {
  it.each(cases.cards)('$name', ({ card, voice, markdown, greetings, tags }) => {
    const data = cardData(card);
    expect(cardVoice(card.name, data)).toEqual(voice);
    expect(cardMarkdown(data)).toBe(markdown);
    expect(cardGreetings(data)).toEqual(greetings);
    expect(cardTags(data)).toEqual(tags);
  });
  it('asks for an uploaded avatar, never a data URL', () => {
    expect(() => cardAvatar({ avatar: 'data:image/png;base64,AAAA' })).toThrow('Upload the avatar first');
    expect(cardAvatar({})).toBeNull();
  });
});
