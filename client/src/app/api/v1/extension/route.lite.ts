// SPDX-License-Identifier: AGPL-3.0-or-later
import { NextResponse } from 'next/server';

/**
 * The server-side extensions this API serves, as server-framework lists its own
 * (`GET /v1/extension`). The UI turns a feature on when the extension serving it is listed, so
 * lite lists exactly what its own routes answer. The wiki has no lite records yet, so it lists
 * none; each joins this list with its first `route.lite.ts` handlers (@zephyrex/lite).
 */
export const LITE_EXTENSIONS: readonly { id: string; name: string; friendly_name: string; description: string }[] = [];

export function GET(): NextResponse {
  return NextResponse.json({ extensions: LITE_EXTENSIONS });
}
