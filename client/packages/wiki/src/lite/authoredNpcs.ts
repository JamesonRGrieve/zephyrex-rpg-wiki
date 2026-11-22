// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * NPCs the GM authors mid-play (operator, 2026-11-22), as the server's rpg_core answers them:
 * - POST /v1/campaign/{id}/fill_person {"person": {person_id, summary?, entry?, personality?,
 *   motive?, voice?, picture?}} → {"person": {id, name, updated}}: an agent fills a person in (the
 *   summary the entry's first paragraph, a Markdown entry, voice personality and speech, a motive,
 *   an https picture link; lite keeps no uploads, so an asset id is refused).
 * - POST /v1/campaign/{id}/elevate {"elevate": {person_id}} → {"elevated": {person_id,
 *   scenario_person_id, scenario_id, created}}: a playthrough's person copied into its scenario,
 *   their place, ties and tags turned to the scenario's own of the same name, their properties
 *   with them; the campaign's person marked "Elevated to"; a second call makes nothing.
 * Lite has one owner, the GM.
 */
import { apiErrorResponse, localOwner, notFound, parseBody, readJsonObject, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { z } from 'zod';
import { plainText } from '../lib/entry';
import { markdownEntry } from '../lib/markdownEntry';
import { voice } from '../lib/names';
import { storedMotivations } from '../lib/routine';
import { prisma } from './db';
import { MADE_IN_PLAY_PROPERTY } from './ensurePerson';

type Context = { params: Promise<Record<string, string>> };
type Row = Record<string, unknown> & { id: string };

export const ELEVATED_PROPERTY = 'Elevated to';
const FILL = z
  .object({
    person_id: z.string(),
    summary: z.string().nullish(),
    entry: z.string().nullish(),
    personality: z.string().nullish(),
    motive: z.string().nullish(),
    voice: z.string().nullish(),
    picture: z.string().nullish(),
  })
  .strict();

async function ownPerson(ownerId: string, campaignId: string, personId: string): Promise<Row> {
  const person = await prisma.person.findFirst({ where: { id: personId, createdById: ownerId, campaignId, deletedAt: null } });
  if (person === null) throw notFound('PersonModel');
  return person as unknown as Row;
}

export async function campaignFillPersonPost(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const campaignId = (await context.params).id ?? '';
    const input = parseBody(FILL, await readJsonObject(request), 'person');
    const person = await ownPerson(owner.id, campaignId, input.person_id);
    const data: Record<string, unknown> = {};
    const line = input.summary?.trim() ?? '';
    if (line || input.entry) {
      const entry = [...(line ? [{ type: 'p', children: [{ text: line }] }] : []), ...markdownEntry(input.entry ?? '')];
      data.entry = JSON.stringify(entry);
      data.description = plainText(entry);
    }
    if (input.personality || input.voice) {
      const held = (typeof person.voice === 'string' && person.voice ? JSON.parse(person.voice) : {}) as Record<string, unknown>;
      if (input.personality) held.personality = input.personality.trim();
      if (input.voice) held.speech = input.voice.trim();
      data.voice = JSON.stringify(voice(held));
    }
    if (input.motive) {
      const held = storedMotivations(typeof person.motivations === 'string' ? person.motivations : null);
      if (!held.includes(input.motive.trim())) data.motivations = JSON.stringify([...held, input.motive.trim()]);
    }
    const picture = input.picture?.trim() ?? '';
    if (picture.startsWith('data:')) throw validationError('Upload the picture first and give its link', 'picture');
    if (picture && !picture.startsWith('https://')) throw validationError('This back end keeps no uploaded pictures: give an https link', 'picture');
    if (picture) data.pictureUrl = picture;
    if (Object.keys(data).length > 0) await prisma.person.update({ where: { id: person.id }, data: { ...data, updatedAt: new Date() } });
    const updated = (['summary', 'entry', 'personality', 'motive', 'voice', 'picture'] as const).filter((key) => input[key]);
    return NextResponse.json({ person: { id: person.id, name: person.name, updated: [...updated].sort() } });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

const ELEVATE = z.object({ person_id: z.string() });
const folded = (name: unknown): string => String(name ?? '').trim().toLocaleLowerCase();

export async function campaignElevatePost(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = localOwner(request);
    const campaignId = (await context.params).id ?? '';
    const input = parseBody(ELEVATE, await readJsonObject(request), 'elevate');
    const person = await ownPerson(owner.id, campaignId, input.person_id);
    const campaign = await prisma.campaign.findFirst({ where: { id: campaignId, createdById: owner.id }, select: { scenarioId: true } });
    const scenarioId = campaign?.scenarioId;
    if (!scenarioId) throw validationError("This campaign isn't a playthrough of a scenario", 'person_id');
    const elevated = await prisma.$transaction(async (tx) => {
      const marks = await tx.recordMetadata.findMany({ where: { targetEntityType: 'person', targetEntityId: person.id } });
      const mark = marks.find((row) => row.key === ELEVATED_PROPERTY);
      if (mark?.value) {
        const twin = await tx.person.findFirst({ where: { id: mark.value, campaignId: scenarioId, deletedAt: null }, select: { id: true } });
        if (twin !== null) return { id: twin.id, created: false };
      }
      const theirs = await tx.person.findMany({ where: { createdById: owner.id, campaignId: scenarioId, deletedAt: null } });
      const now = new Date();
      const setMark = async (twinId: string): Promise<void> => {
        await tx.recordMetadata.deleteMany({ where: { targetEntityType: 'person', targetEntityId: person.id, key: ELEVATED_PROPERTY } });
        await tx.recordMetadata.create({ data: { createdById: owner.id, targetEntityType: 'person', targetEntityId: person.id, key: ELEVATED_PROPERTY, value: twinId, valueType: 'text', ordinal: 0, isPrivate: true, updatedAt: now } });
      };
      const existing = theirs.find((row) => folded(row.name) === folded(person.name));
      if (existing !== undefined) {
        await setMark(existing.id);
        return { id: existing.id, created: false };
      }
      // Their place: the scenario's of the same name, or the setting's canon kept as is.
      let locationId: string | null = null;
      if (typeof person.locationId === 'string') {
        const place = await tx.location.findFirst({ where: { id: person.locationId } });
        if (place !== null) {
          const match = await tx.location.findFirst({ where: { createdById: owner.id, campaignId: scenarioId, deletedAt: null, name: place.name } });
          locationId = match?.id ?? (place.campaignId ? null : place.id);
        }
      }
      const twinId = crypto.randomUUID();
      const { id: _id, createdAt: _created, updatedAt: _updated, ...columns } = person;
      await tx.person.create({ data: { ...(columns as object), id: twinId, campaignId: scenarioId, locationId, createdById: owner.id, updatedAt: now } as never });
      // Tags: a campaign's own tag becomes the scenario's of the same name and kind (made if missing).
      for (const link of await tx.entityTaxon.findMany({ where: { targetEntityType: 'person', targetEntityId: person.id } })) {
        const taxon = await tx.taxon.findFirst({ where: { id: link.taxonId } });
        if (taxon === null) continue;
        let taxonId = taxon.id;
        if (taxon.campaignId === campaignId) {
          const same = await tx.taxon.findFirst({ where: { createdById: owner.id, campaignId: scenarioId, name: taxon.name, kind: taxon.kind, deletedAt: null } });
          taxonId = same?.id ?? (await tx.taxon.create({ data: { createdById: owner.id, name: taxon.name, kind: taxon.kind, campaignId: scenarioId, updatedAt: now } })).id;
        }
        await tx.entityTaxon.create({ data: { createdById: owner.id, taxonId, targetEntityType: 'person', targetEntityId: twinId, updatedAt: now } });
      }
      // Ties to organisations and people: the scenario's of the same name, or the setting's canon.
      const factions = await tx.faction.findMany({ where: { createdById: owner.id, campaignId: scenarioId, deletedAt: null } });
      for (const tie of await tx.relationship.findMany({ where: { personId: person.id } })) {
        const { id: _tieId, createdAt: _tieCreated, updatedAt: _tieUpdated, mirrorRelationshipId: _mirror, ...tieColumns } = tie;
        const remap = async (id: string | null, kind: 'faction' | 'person'): Promise<string | null> => {
          if (!id) return null;
          const row = kind === 'faction' ? await tx.faction.findFirst({ where: { id } }) : await tx.person.findFirst({ where: { id } });
          if (row === null) return null;
          if (!row.campaignId) return row.id;
          const pool: { id: string; name: string }[] = kind === 'faction' ? factions : theirs;
          return pool.find((one) => folded(one.name) === folded(row.name))?.id ?? null;
        };
        const targetFactionId = await remap(tie.targetFactionId, 'faction');
        const targetPersonId = await remap(tie.targetPersonId, 'person');
        if (targetFactionId || targetPersonId) {
          await tx.relationship.create({ data: { ...tieColumns, personId: twinId, targetFactionId, targetPersonId, createdById: owner.id, updatedAt: now } });
        }
      }
      // Properties, not the marks of play.
      const kept = marks.filter((row) => row.key !== ELEVATED_PROPERTY && row.key !== MADE_IN_PLAY_PROPERTY);
      if (kept.length > 0) {
        await tx.recordMetadata.createMany({
          data: kept.map((row) => ({ createdById: owner.id, targetEntityType: 'person', targetEntityId: twinId, key: row.key, value: row.value, valueType: row.valueType, ordinal: row.ordinal, isPrivate: row.isPrivate, updatedAt: now })),
        });
      }
      await setMark(twinId);
      return { id: twinId, created: true };
    });
    return NextResponse.json({ elevated: { person_id: person.id, scenario_person_id: elevated.id, scenario_id: scenarioId, created: elevated.created } });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
