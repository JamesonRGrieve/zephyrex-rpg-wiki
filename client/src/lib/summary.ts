// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A record's summary for a lorebook entry (rpg-ai A15), the same rule as the server's
 * (server/extensions/wiki_shared/Summary.py) and rpg-ai's, held to contract/summary-cases.json:
 * whitespace runs become one space; within the limit the text stands; longer, it is cut at the last
 * space leaving room for "…" (or at the limit less one when there is none), trimmed, and "…" added.
 */
import { LIMITS } from '~/contract';

export function summary(text: string | null | undefined, limit: number = LIMITS.summary_characters): string {
  const flat = (text ?? '').replace(/\s+/g, ' ').trim();
  if (flat.length <= limit) return flat;
  const room = flat.slice(0, limit - 1);
  const cut = room.lastIndexOf(' ');
  return `${(cut > 0 ? room.slice(0, cut) : room).trimEnd()}…`;
}
