// SPDX-License-Identifier: AGPL-3.0-or-later
// GET /v1/extension: the extensions the wiki's lite routes serve, as server-framework lists its own.
import { WIKI_LITE_EXTENSIONS } from '@zephyrex-rpg/wiki/lite';
import { NextResponse } from 'next/server';

export function GET(): NextResponse {
  return NextResponse.json({ extensions: WIKI_LITE_EXTENSIONS });
}
