// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The world tick, as the server's rpg_core answers it: a campaign's clock (GET and POST
 * /v1/campaign/{id}/clock) and people moved by the GM (POST and GET /v1/person_move), each move
 * recorded with where from, to where, when in-world and why. Lite has one owner, the GM.
 */
import { apiErrorResponse, localOwner, notFound, parseBody, readJsonObject, STATUS, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { z } from 'zod';
import { LIMITS } from '../contract';
import { clock } from '../lib/routine';
import { prisma } from './db';

type Context = { params: Promise<Record<string, string>> };
type MoveRow = Awaited<ReturnType<typeof prisma.personMove.findFirstOrThrow>>;

async function campaignOf(ownerId: string, id: string): Promise<{ id: string; clockMinutes: number | null; settingId: string | null }> {
  const campaign = await prisma.campaign.findFirst({ where: { id, createdById: ownerId }, select: { id: true, clockMinutes: true, settingId: true } });
  if (campaign === null) throw notFound('CampaignModel');
  return campaign;
}

export async function clockGet(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const campaign = await campaignOf(owner.id, (await context.params).id ?? '');
    return NextResponse.json({ ...clock(campaign.clockMinutes), reason: null });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

const advance = z.object({ minutes: z.number().int(), reason: z.string().nullish() });

export async function clockPost(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const campaign = await campaignOf(owner.id, (await context.params).id ?? '');
    const input = parseBody(advance, await readJsonObject(request), 'clock');
    if (input.minutes < 1 || input.minutes > LIMITS.clock_advance_minutes)
      throw validationError(`The clock advances 1 to ${LIMITS.clock_advance_minutes} minutes at a time`, 'minutes');
    const now = clock(campaign.clockMinutes).minutes + input.minutes;
    await prisma.campaign.update({ where: { id: campaign.id }, data: { clockMinutes: now, updatedAt: new Date() } });
    return NextResponse.json({ ...clock(now), reason: input.reason?.trim() || null });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

function moveOf(row: MoveRow): Record<string, unknown> {
  return {
    id: row.id,
    person_id: row.personId,
    campaign_id: row.campaignId,
    from_location_id: row.fromLocationId,
    to_location_id: row.toLocationId,
    at_minutes: row.atMinutes,
    reason: row.reason,
    user_id: null,
    created_at: row.createdAt.toISOString(),
    updated_at: row.updatedAt.toISOString(),
  };
}

const move = z.object({ person_id: z.string().min(1), to_location_id: z.string().min(1), reason: z.string().nullish() });

/** POST /v1/person_move: the person goes there (a place in their campaign or its setting's canon), and the move is kept. */
export async function personMovePost(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const input = parseBody(move, await readJsonObject(request), 'person_move');
    const reason = input.reason?.trim() ?? '';
    if (reason.length > LIMITS.move_reason_characters) throw validationError(`A move's reason has at most ${LIMITS.move_reason_characters} characters`, 'reason');
    const person = await prisma.person.findFirst({ where: { id: input.person_id, createdById: owner.id, deletedAt: null } });
    if (person === null) throw notFound('PersonModel');
    const place = await prisma.location.findFirst({ where: { id: input.to_location_id, createdById: owner.id, deletedAt: null } });
    if (place === null) throw notFound('LocationModel');
    const campaign = person.campaignId === null ? null : await campaignOf(owner.id, person.campaignId);
    const settingId = person.settingId ?? campaign?.settingId ?? null;
    const inCampaign = person.campaignId !== null && place.campaignId === person.campaignId;
    const inCanon = place.campaignId === null && settingId !== null && place.settingId === settingId;
    if (!inCampaign && !inCanon) throw validationError("That place isn't in the person's campaign or its setting", 'to_location_id');
    const stamp = new Date();
    const [, row] = await prisma.$transaction([
      prisma.person.update({ where: { id: person.id }, data: { locationId: place.id, updatedAt: stamp } }),
      prisma.personMove.create({
        data: {
          createdById: owner.id,
          personId: person.id,
          campaignId: person.campaignId,
          fromLocationId: person.locationId,
          toLocationId: place.id,
          atMinutes: campaign === null ? null : clock(campaign.clockMinutes).minutes,
          reason: reason || null,
          updatedAt: stamp,
        },
      }),
    ]);
    return NextResponse.json({ person_move: moveOf(row) }, { status: STATUS.CREATED });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

/** GET /v1/person_move?person_id=: where a person has been moved, oldest first. */
export async function personMovesGet(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const personId = request.nextUrl.searchParams.get('person_id');
    const rows = await prisma.personMove.findMany({
      where: { createdById: owner.id, ...(personId ? { personId } : {}) },
      orderBy: [{ createdAt: 'asc' }, { id: 'asc' }],
    });
    return NextResponse.json({ person_moves: rows.map(moveOf) });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
