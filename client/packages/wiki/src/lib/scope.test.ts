// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import { isCanon, scopeFields, scopeQuery, settingOf, settingScope } from './scope';

describe('scope', () => {
  it('reads a campaign and a setting', () => {
    expect([settingOf('c1'), settingOf(settingScope('s1'))]).toEqual([null, 's1']);
    expect([scopeQuery('c1'), scopeQuery('setting-s1')]).toEqual([{ campaign_id: 'c1' }, { setting_id: 's1' }]);
    expect([scopeFields('c1'), scopeFields('setting-s1')]).toEqual([{ campaign_id: 'c1' }, { setting_id: 's1', campaign_id: null }]);
    expect([isCanon({ campaign_id: null }), isCanon({ campaign_id: 'c1' })]).toEqual([true, false]);
  });
});
