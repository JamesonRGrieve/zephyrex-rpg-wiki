// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * rpg-ai A24's session reports in the lite edition, as the server's rpg_core answers them: a report
 * is a journal of kind session_report in its campaign. Writing checks the campaign is the owner's
 * (404) and that each mention is a record in it (422); reading answers the review sheet's shape.
 */
import { recordError, validationError } from '@zephyrex/lite';
import { z } from 'zod';
import { ENTITY_TYPES, LIMITS } from '~/contract';
import { plainText } from '~/lib/entry';
import { prisma } from '~/lib/prisma';
import { mentionsIn, type NamedMention, reportEntry } from '~/lib/report';
import { journals } from '~/lib/worldRecords';

export const sessionReportSchema = z.object({
  campaign_id: z.string().min(1),
  title: z.string().trim().min(1, 'A name is required').max(LIMITS.name_characters),
  body: z.union([z.string(), z.array(z.unknown())]),
  occurred_at: z.coerce.date().nullable().default(null),
  session_number: z.number().int().min(1).nullable().default(null),
  mentions: z
    .array(z.object({ target_entity_type: z.enum(ENTITY_TYPES as [string, ...string[]]), target_entity_id: z.string().min(1) }))
    .max(LIMITS.report_mentions)
    .default([]),
});
export type SessionReportInput = z.infer<typeof sessionReportSchema>;

async function nameIn(ownerId: string, campaignId: string, type: string, id: string): Promise<string | null> {
  const where = { id, createdById: ownerId, deletedAt: null };
  const select = { name: true, campaignId: true } as const;
  const row =
    type === 'person'
      ? await prisma.person.findFirst({ where, select })
      : type === 'location'
        ? await prisma.location.findFirst({ where, select })
        : type === 'faction'
          ? await prisma.faction.findFirst({ where, select })
          : type === 'item'
            ? await prisma.item.findFirst({ where, select })
            : type === 'hook'
              ? await prisma.hook.findFirst({ where, select })
              : await prisma.journal.findFirst({ where, select });
  if (row === null) throw validationError(`No ${type} ${id} to mention`, 'mentions');
  return row.campaignId === campaignId ? row.name : null;
}

export async function writeSessionReport(ownerId: string, report: SessionReportInput): Promise<string> {
  if ((await prisma.campaign.count({ where: { id: report.campaign_id, createdById: ownerId } })) === 0)
    throw recordError(404, 'CampaignModel not found');
  const named: NamedMention[] = [];
  for (const mention of report.mentions) {
    const found = await nameIn(ownerId, report.campaign_id, mention.target_entity_type, mention.target_entity_id);
    if (found === null) throw validationError('That record is not in this campaign', 'mentions');
    named.push({ ...mention, name: found });
  }
  const row = await journals.insert(
    ownerId,
    {
      name: report.title,
      description: '',
      entry: reportEntry(report.body, named),
      kind: 'session_report',
      location_id: null,
      author_person_id: null,
      session_number: report.session_number,
      occurred_at: report.occurred_at,
      campaign_id: report.campaign_id,
      // A report is the campaign's own record; its setting comes with the campaign (S6).
      setting_id: null,
      canon_level: null,
      is_template: null,
    },
    new Date(),
  );
  return row.id;
}

export async function readSessionReport(ownerId: string, id: string): Promise<Record<string, unknown>> {
  const row = await prisma.journal.findFirst({ where: { id, createdById: ownerId, deletedAt: null, kind: 'session_report' } });
  if (row === null) throw recordError(404, 'Not a session report');
  const entry = row.entry === null ? [] : (JSON.parse(row.entry) as unknown[]);
  return {
    id: row.id,
    campaign_id: row.campaignId,
    title: row.name,
    body: row.entry ?? '[]',
    text: entry.length === 0 ? row.description : plainText(entry),
    occurred_at: row.occurredAt?.toISOString() ?? null,
    session_number: row.sessionNumber,
    mentions: mentionsIn(entry as never),
    updated_at: row.updatedAt.toISOString(),
  };
}
