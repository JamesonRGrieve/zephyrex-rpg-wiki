// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * POST /v1/campaign/{id}/person {"person": {name, summary?}} → {"person": {id, name, created}}, as the
 * server's rpg_core answers it (ensure_person; Parity, 2026-11-21: a narrator's unnamed NPC who
 * speaks joins the cast): the campaign's person of that name, case aside, or a new NPC with the
 * summary as its entry, GM only and marked as made in play. Lite has one owner, the GM.
 */
import { apiErrorResponse, localOwner, notFound, parseBody, readJsonObject } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { z } from 'zod';
import { GM_ONLY_PROPERTY, LIMITS } from '../contract';
import { prisma } from './db';

type Context = { params: Promise<Record<string, string>> };

/** The property that marks a person the narrator brought in (the server's MADE_IN_PLAY_PROPERTY). */
export const MADE_IN_PLAY_PROPERTY = 'Made in play';

const asked = z.object({ name: z.string().trim().min(1).max(LIMITS.name_characters), summary: z.string().nullish() });

export async function campaignPersonPost(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const campaignId = (await context.params).id ?? '';
    const input = parseBody(asked, await readJsonObject(request), 'person');
    const campaign = await prisma.campaign.findFirst({ where: { id: campaignId, createdById: owner.id }, select: { id: true } });
    if (campaign === null) throw notFound('CampaignModel');
    const folded = input.name.toLocaleLowerCase();
    const people = await prisma.person.findMany({ where: { campaignId, createdById: owner.id, deletedAt: null }, select: { id: true, name: true } });
    const held = people.find((one) => one.name.trim().toLocaleLowerCase() === folded);
    if (held !== undefined) return NextResponse.json({ person: { id: held.id, name: held.name, created: false } });
    const line = input.summary?.trim() ?? '';
    const now = new Date();
    const made = await prisma.$transaction(async (tx) => {
      const person = await tx.person.create({
        data: {
          createdById: owner.id,
          name: input.name,
          kind: 'npc',
          campaignId,
          provenance: 'homebrew',
          entry: line ? JSON.stringify([{ type: 'p', children: [{ text: line }] }]) : null,
          updatedAt: now,
        },
        select: { id: true, name: true },
      });
      const property = (key: string, value: string, valueType: string) => ({
        createdById: owner.id,
        targetEntityType: 'person',
        targetEntityId: person.id,
        key,
        value,
        valueType,
        ordinal: 0,
        isPrivate: true,
        updatedAt: now,
      });
      await tx.recordMetadata.createMany({ data: [property(GM_ONLY_PROPERTY, 'true', 'boolean'), property(MADE_IN_PLAY_PROPERTY, 'By the narrator', 'text')] });
      return person;
    });
    return NextResponse.json({ person: { id: made.id, name: made.name, created: true } });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
