// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * GET /v1/campaign/{id}/framing, as the server's rpg_core campaign_framing answers it (Parity,
 * 2026-11-22): a campaign's description, its framing journal's public text and GM part
 * (lib/framing), its setting's tone and its play styles; a playthrough with none of its own takes
 * its scenario's (from_scenario). Lite has one owner, the GM, who sees the GM notes.
 */
import { apiErrorResponse, localOwner, notFound } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { GM_ONLY_PROPERTY } from '../contract';
import { framingParts } from '../lib/framing';
import { prisma } from './db';

type Context = { params: Promise<Record<string, string>> };
type Held = { description: string; framing: string; gm: string; styles: string[] };

async function framingOf(ownerId: string, campaign: { id: string; description: string }): Promise<Held> {
  const journals = await prisma.journal.findMany({
    where: { createdById: ownerId, campaignId: campaign.id, kind: 'campaign_framing', deletedAt: null, OR: [{ isTemplate: null }, { isTemplate: false }] },
    orderBy: { name: 'asc' },
    select: { id: true, entry: true },
  });
  let framing = '';
  let gm = '';
  const first = journals[0];
  if (first !== undefined) {
    const parts = framingParts(first.entry);
    framing = parts.public;
    gm = parts.gm;
    const secret = await prisma.recordMetadata.findFirst({ where: { targetEntityType: 'journal', targetEntityId: first.id, key: GM_ONLY_PROPERTY } });
    if (secret?.value?.trim().toLowerCase() === 'true') {
      gm = [framing, gm].filter((part) => part !== '').join('\n\n');
      framing = '';
    }
  }
  const links = await prisma.entityTaxon.findMany({ where: { targetEntityType: 'campaign', targetEntityId: campaign.id }, select: { taxonId: true } });
  const taxa = await prisma.taxon.findMany({ where: { id: { in: links.map((link) => link.taxonId) }, kind: 'play_style' }, select: { name: true } });
  return { description: campaign.description, framing, gm, styles: taxa.map((taxon) => taxon.name).sort() };
}

export async function campaignFramingGet(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const id = (await context.params).id ?? '';
    const campaign = await prisma.campaign.findFirst({ where: { id, createdById: owner.id }, select: { id: true, name: true, description: true, settingId: true, scenarioId: true } });
    if (campaign === null) throw notFound('CampaignModel');
    let held = await framingOf(owner.id, campaign);
    let fromScenario = false;
    if (!held.description && !held.framing && !held.gm && campaign.scenarioId) {
      const scenario = await prisma.campaign.findFirst({ where: { id: campaign.scenarioId, createdById: owner.id }, select: { id: true, description: true } });
      if (scenario !== null) {
        const theirs = await framingOf(owner.id, scenario);
        if (theirs.description || theirs.framing || theirs.gm) {
          held = { ...theirs, styles: held.styles.length > 0 ? held.styles : theirs.styles };
          fromScenario = true;
        }
      }
    }
    const setting = campaign.settingId ? await prisma.setting.findFirst({ where: { id: campaign.settingId }, select: { id: true, name: true, description: true } }) : null;
    return NextResponse.json({
      campaign_framing: {
        campaign_id: campaign.id,
        name: campaign.name,
        description: held.description,
        framing: held.framing,
        gm_notes: held.gm,
        setting: setting === null ? null : { id: setting.id, name: setting.name, tone: setting.description },
        play_styles: held.styles,
        from_scenario: fromScenario,
        // As the server's: its game system (zephyrex-vtt's game_systems), which lite doesn't serve.
        game_system: null,
      },
    });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
