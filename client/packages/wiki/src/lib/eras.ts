// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Era scoping (contract/era-cases.json; the server's wiki_shared/Eras.py computes the same): a
 * setting's canon record with eras reaches a campaign only when they share one; one with none
 * reaches every campaign; a campaign with no era sees all.
 */
export const ERA = 'era';

export const eraNames = (values: Iterable<string>): Set<string> =>
  new Set([...values].map((value) => value.trim().toLocaleLowerCase()).filter((value) => value !== ''));

export function eraVisible(recordEras: Iterable<string>, campaignEras: Iterable<string>): boolean {
  const record = eraNames(recordEras);
  const campaign = eraNames(campaignEras);
  return record.size === 0 || campaign.size === 0 || [...record].some((era) => campaign.has(era));
}
