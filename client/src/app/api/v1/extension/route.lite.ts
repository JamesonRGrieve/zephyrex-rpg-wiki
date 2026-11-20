// SPDX-License-Identifier: AGPL-3.0-or-later
import { NextResponse } from 'next/server';

/**
 * The server-side extensions this API serves, as server-framework lists its own
 * (`GET /v1/extension`). The UI turns a feature on when the extension serving it is listed
 * (src/features/capabilities.ts), so lite lists exactly what its own routes answer: worlds
 * (rpg_core's campaigns), places (world_spatial) and people (genealogy's Person). Accounts stay off
 * because auth_session is absent.
 */
export const LITE_EXTENSIONS = [
  { id: 'lite-genealogy', name: 'genealogy', friendly_name: 'People', description: 'People and creatures' },
  { id: 'lite-world_spatial', name: 'world_spatial', friendly_name: 'Places', description: 'Locations as a tree, at every scale' },
  { id: 'lite-rpg_core', name: 'rpg_core', friendly_name: 'Worlds', description: 'Worlds, and who and what is in each' },
] as const;

export function GET(): NextResponse {
  return NextResponse.json({ extensions: LITE_EXTENSIONS });
}
