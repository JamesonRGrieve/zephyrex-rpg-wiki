// @vitest-environment node
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/tts-voice-cases.json';
import { ttsVoice } from './names';

describe('ttsVoice (contract/tts-voice-cases.json)', () => {
  it.each(cases.cases)('$name', (one) => {
    if ('error' in one && one.error) expect(() => ttsVoice(one.value)).toThrow(one.error);
    else expect(ttsVoice(one.value)).toBe('stored' in one ? one.stored : null);
  });
});
