// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * GET /v1/campaign_document?campaign_id= (Parity's data bank), as the server's rpg_core
 * campaign_documents answers it: {"campaign_documents": [{id, kind, name, text, gm_only}]}, the full
 * plain text of each of the campaign's records (journals first; templates and records with no text
 * left out), unpaged. gm_only as in world_entities: its private "GM only" property is "true".
 */
import { apiErrorResponse, localOwner, recordError, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { GM_ONLY_PROPERTY } from '../contract';
import { orderedDocuments } from '../lib/documents';
import { prisma } from './db';

export async function campaignDocumentsGet(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const campaignId = request.nextUrl.searchParams.get('campaign_id') ?? '';
    if (campaignId === '') throw validationError('Name a campaign_id', 'campaign_id');
    if ((await prisma.campaign.count({ where: { id: campaignId, createdById: owner.id } })) === 0) throw recordError(404, 'CampaignModel not found');
    const where = { createdById: owner.id, campaignId, deletedAt: null, OR: [{ isTemplate: null }, { isTemplate: false }] };
    const select = { id: true, name: true, description: true } as const;
    const [journals, locations, persons, factions, items, hooks] = await Promise.all([
      prisma.journal.findMany({ where, select }),
      prisma.location.findMany({ where, select }),
      prisma.person.findMany({ where, select }),
      prisma.faction.findMany({ where, select }),
      prisma.item.findMany({ where, select }),
      prisma.hook.findMany({ where, select }),
    ]);
    const records = Object.entries({ journal: journals, location: locations, person: persons, faction: factions, item: items, hook: hooks }).flatMap(([kind, rows]) =>
      rows.map((row) => ({ id: row.id, kind, name: row.name, text: row.description })),
    );
    const secret = new Set(
      (
        await prisma.recordMetadata.findMany({
          where: { key: GM_ONLY_PROPERTY, targetEntityId: { in: records.map((record) => record.id) } },
          select: { targetEntityType: true, targetEntityId: true, value: true },
        })
      )
        .filter((row) => (row.value ?? '').trim().toLowerCase() === 'true')
        .map((row) => `${row.targetEntityType}:${row.targetEntityId}`),
    );
    const documents = orderedDocuments(records).map((document) => ({ ...document, gm_only: secret.has(`${document.kind}:${document.id}`) }));
    return NextResponse.json({ campaign_documents: documents });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
