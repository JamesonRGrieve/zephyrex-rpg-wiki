// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The records another era holds, kept from a campaign's view of its setting's canon (operator,
 * 2026-11-23: Reality's eras work like the 40k lines), as the server's rpg_core era_excluded: none
 * when the campaign has no era; else every record whose eras (taxa of kind era) it shares none of.
 * Era-less canon is never excluded.
 */
import { ERA, eraVisible } from '../lib/eras';
import { prisma } from './db';

export async function eraExcluded(ownerId: string, campaignId: string): Promise<string[]> {
  const taxa = await prisma.taxon.findMany({ where: { createdById: ownerId, kind: ERA, deletedAt: null }, select: { id: true, name: true } });
  if (taxa.length === 0) return [];
  const names = new Map(taxa.map((taxon) => [taxon.id, taxon.name]));
  const links = await prisma.entityTaxon.findMany({ where: { taxonId: { in: [...names.keys()] } }, select: { taxonId: true, targetEntityId: true } });
  const erasOf = new Map<string, string[]>();
  for (const link of links) erasOf.set(link.targetEntityId, [...(erasOf.get(link.targetEntityId) ?? []), names.get(link.taxonId) ?? '']);
  const own = erasOf.get(campaignId) ?? [];
  if (own.length === 0) return [];
  return [...erasOf].filter(([target, eras]) => target !== campaignId && !eraVisible(eras, own)).map(([target]) => target);
}
