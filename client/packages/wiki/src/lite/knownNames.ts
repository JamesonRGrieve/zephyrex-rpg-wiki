// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * GET /v1/campaign/{id}/known_names → {known_names: {party, by_pc}}, as the server's rpg_core
 * known_names (operator, 2026-11-25: "NPCs should have generic descriptions unless the player knows
 * their name which gets replaced as names are learned"): which persons each PC of the campaign
 * knows the name of, and which the party does. Knowing of a person (a known fact with no text) is
 * knowing their name; a fact with text alone is not; the PCs know each other. Lite has one owner,
 * who sees every PC.
 */
import { apiErrorResponse, localOwner, notFound } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { prisma } from './db';

type Context = { params: Promise<Record<string, string>> };

export interface KnownNames {
  party: string[];
  by_pc: Record<string, string[]>;
}

export interface FactRow {
  personId: string;
  targetEntityType: string;
  targetEntityId: string;
  text: string | null;
}

/** Whose names each PC knows (themselves and the party, and whom they know of), and the party. */
export function knownNamesOf(pcs: readonly string[], facts: readonly FactRow[]): KnownNames {
  const sorted = [...new Set(pcs)].sort();
  if (sorted.length === 0) return { party: [], by_pc: {} };
  const knows = new Map(sorted.map((pc) => [pc, new Set(sorted)]));
  for (const fact of facts) {
    if (fact.targetEntityType === 'person' && !(fact.text ?? '').trim()) knows.get(fact.personId)?.add(fact.targetEntityId);
  }
  const party = new Set<string>();
  for (const known of knows.values()) for (const one of known) party.add(one);
  return { party: [...party].sort(), by_pc: Object.fromEntries(sorted.map((pc) => [pc, [...(knows.get(pc) ?? [])].sort()])) };
}

export async function campaignKnownNamesGet(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const id = (await context.params).id ?? '';
    if ((await prisma.campaign.count({ where: { id, createdById: owner.id } })) === 0) throw notFound('CampaignModel');
    const pcs = await prisma.person.findMany({
      where: { createdById: owner.id, campaignId: id, kind: 'pc', deletedAt: null, OR: [{ isTemplate: null }, { isTemplate: false }] },
      select: { id: true },
    });
    const ids = pcs.map((one) => one.id);
    const facts = ids.length === 0 ? [] : await prisma.knownFact.findMany({ where: { personId: { in: ids } }, select: { personId: true, targetEntityType: true, targetEntityId: true, text: true } });
    return NextResponse.json({ known_names: knownNamesOf(ids, facts) });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
