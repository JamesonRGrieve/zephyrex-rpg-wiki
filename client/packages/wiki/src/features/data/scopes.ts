// SPDX-License-Identifier: AGPL-3.0-or-later
/** A scope's name and setting: a campaign's (and the setting it takes place in), or a setting's own. */
import { settingOf } from '../../lib/scope';
import { settings, worlds } from './records';

export interface ScopeInfo {
  name: string | undefined;
  /** The setting: the scope's own, or the campaign's. */
  settingId: string | null | undefined;
  isSetting: boolean;
}

export function useScope(scope: string): ScopeInfo {
  const setting = settingOf(scope);
  const campaign = worlds.useOne(setting === null ? scope : null);
  const own = settings.useOne(setting ?? campaign.data?.setting_id ?? null);
  return setting === null
    ? { name: campaign.data?.name, settingId: campaign.data === undefined ? undefined : (campaign.data.setting_id ?? null), isSetting: false }
    : { name: own.data?.name, settingId: setting, isSetting: true };
}
