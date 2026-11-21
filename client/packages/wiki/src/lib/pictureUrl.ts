// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A record's picture by link (contract/picture-url-cases.json), as the server's wiki_shared/Pictures.py
 * reads it: an https address, trimmed; an empty one is none. Shown as it is, with no referrer.
 */
import { LIMITS } from '../contract';

export class PictureUrlError extends Error {}

export function pictureUrl(value: unknown): string | null {
  if (value === undefined || value === null) return null;
  if (typeof value !== 'string') throw new PictureUrlError('A picture link is an https address');
  const text = value.trim();
  if (text === '') return null;
  if (text.length > LIMITS.picture_url_characters) throw new PictureUrlError(`A picture link has at most ${LIMITS.picture_url_characters} characters`);
  let parsed: URL;
  try {
    parsed = new URL(text);
  } catch {
    throw new PictureUrlError('A picture link is an https address');
  }
  // A host right after the scheme: URL would read "https:///a.png" as host a.png, where the server finds none.
  if (parsed.protocol !== 'https:' || !/^https:\/\/[^/?#\s]/i.test(text)) throw new PictureUrlError('A picture link is an https address');
  return text;
}
