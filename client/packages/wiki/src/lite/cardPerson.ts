// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * POST /v1/campaign/card_person {"card": {name, description, personality, scenario, first_message,
 * example_messages, alternate_greetings, avatar, tags, …}} → 201 {person_id, campaign_id}: a
 * SillyTavern character card as an NPC of the owner's "Characters" campaign, as the server's
 * rpg_core import_card_person (lib/cards, contract/card-cases.json). The avatar is an https link
 * (lite keeps no uploads). Each call makes a person.
 */
import { apiErrorResponse, localOwner, parseBody, readJsonObject, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { z } from 'zod';
import { CHARACTERS, cardAvatar, cardData, cardGreetings, cardMarkdown, cardTags, cardVoice } from '../lib/cards';
import { plainText } from '../lib/entry';
import { markdownEntry } from '../lib/markdownEntry';
import { voice } from '../lib/names';
import { prisma } from './db';

const CARD = z.object({ name: z.string().trim().min(1).max(200) }).passthrough();
const GREETINGS_PROPERTY = 'Alternate greetings';

export async function campaignCardPersonPost(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const card = parseBody(CARD, await readJsonObject(request), 'card') as Record<string, unknown> & { name: string };
    let avatar: string | null;
    try {
      avatar = cardAvatar(card);
    } catch (error) {
      throw validationError(error instanceof Error ? error.message : String(error), 'avatar');
    }
    if (avatar !== null && !avatar.startsWith('https://')) throw validationError('This back end keeps no uploaded pictures: give an https link', 'avatar');
    const data = cardData(card);
    const now = new Date();
    const campaign =
      (await prisma.campaign.findFirst({ where: { createdById: owner.id, name: CHARACTERS, OR: [{ isScenario: null }, { isScenario: false }] }, orderBy: { createdAt: 'asc' } })) ??
      (await prisma.campaign.create({ data: { createdById: owner.id, name: CHARACTERS, description: 'Characters to chat with outside any scenario.', updatedAt: now } }));
    const markdown = cardMarkdown(data);
    const entry = markdown ? markdownEntry(markdown) : null;
    const person = await prisma.person.create({
      data: {
        createdById: owner.id,
        name: card.name.trim(),
        kind: 'npc',
        campaignId: campaign.id,
        description: entry === null ? '' : plainText(entry),
        entry: entry === null ? null : JSON.stringify(entry),
        voice: JSON.stringify(voice(cardVoice(card.name.trim(), data))),
        pictureUrl: avatar,
        updatedAt: now,
      },
    });
    const greetings = cardGreetings(data);
    if (greetings.length > 0)
      await prisma.recordMetadata.create({
        data: { createdById: owner.id, targetEntityType: 'person', targetEntityId: person.id, key: GREETINGS_PROPERTY, value: greetings.join('\n\n'), valueType: 'text', isPrivate: true, updatedAt: now },
      });
    for (const tag of cardTags(data)) {
      // eslint-disable-next-line no-await-in-loop -- one tag at a time keeps each taxon single
      const taxon =
        (await prisma.taxon.findFirst({ where: { createdById: owner.id, campaignId: campaign.id, kind: 'tag', name: tag, deletedAt: null } })) ??
        (await prisma.taxon.create({ data: { createdById: owner.id, campaignId: campaign.id, kind: 'tag', name: tag, updatedAt: now } }));
      // eslint-disable-next-line no-await-in-loop -- as above
      await prisma.entityTaxon.create({ data: { createdById: owner.id, taxonId: taxon.id, targetEntityType: 'person', targetEntityId: person.id, updatedAt: now } });
    }
    return NextResponse.json({ person_id: person.id, campaign_id: campaign.id }, { status: 201 });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
