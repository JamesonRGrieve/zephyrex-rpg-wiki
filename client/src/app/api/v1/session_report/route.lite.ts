// SPDX-License-Identifier: AGPL-3.0-or-later
// POST /v1/session_report — write a session report into a campaign (rpg-ai A24), as the server answers.
import { apiErrorResponse, localOwner, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { readSessionReport, sessionReportSchema, writeSessionReport } from '~/lib/sessionReports';

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const body = (await request.json()) as { session_report?: unknown };
    const parsed = sessionReportSchema.safeParse(body.session_report);
    if (!parsed.success) throw validationError(parsed.error.issues[0]?.message ?? 'Not a session report', 'session_report');
    const id = await writeSessionReport(owner.id, parsed.data);
    return NextResponse.json({ session_report: await readSessionReport(owner.id, id) }, { status: 201 });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
