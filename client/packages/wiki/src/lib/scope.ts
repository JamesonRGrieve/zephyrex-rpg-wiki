// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * What a page is about (operator, 2026-11-21: settings and campaigns): a campaign, by its id, or a
 * setting's canon, by `setting-<id>`. The one path segment both kinds of page take, so every link
 * (recordPath, kindPath…) works for either; this turns it into a list's filter and a new record's
 * fields.
 */
const SETTING = 'setting-';

/** A setting's canon as a page's scope. */
export const settingScope = (settingId: string): string => `${SETTING}${settingId}`;

/** The setting a scope names, or null for a campaign. */
export const settingOf = (scope: string): string | null => (scope.startsWith(SETTING) ? scope.slice(SETTING.length) : null);

/** A list's filter for the scope's own records. */
export function scopeQuery(scope: string): Record<string, string> {
  const setting = settingOf(scope);
  return setting === null ? { campaign_id: scope } : { setting_id: setting };
}

/** A new record's fields for the scope: in the campaign, or the setting's canon (no campaign). */
export function scopeFields(scope: string): { campaign_id: string } | { setting_id: string; campaign_id: null } {
  const setting = settingOf(scope);
  return setting === null ? { campaign_id: scope } : { setting_id: setting, campaign_id: null };
}

/** A setting's canon is its records with no campaign; a list by setting_id keeps only those. */
export const isCanon = (row: { campaign_id?: string | null }): boolean => row.campaign_id === null || row.campaign_id === undefined;
