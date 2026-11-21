// SPDX-License-Identifier: AGPL-3.0-or-later
// GET /v1/session_report/{id} — a session report for its review sheet (rpg-ai A24).
import { apiErrorResponse, localOwner } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { readSessionReport } from '~/lib/sessionReports';

export async function GET(request: NextRequest, context: { params: Promise<{ id: string }> }): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const { id } = await context.params;
    return NextResponse.json({ session_report: await readSessionReport(owner.id, id) });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
