// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * POST /v1/campaign/{id}/lore_search {"lore_search": {text, k, token_budget, kinds, tags,
 * include_setting}}: the campaign's lore passages for a text, as the server's rpg_core answers it
 * (LoreSearch.py): the records the text names first, then FTS5, trigram and sqlite-vec ranks fused
 * (lib/loreIndex fuse), kept to the campaign's scope and packed to the token budget. Each search
 * first brings the index up to date with the owner's changed records; waiting passages are embedded
 * after the answer, a batch at a time (WIKI_EMBED_URL and WIKI_EMBED_MODEL, or registerLoreEmbedder).
 */
import { apiErrorResponse, localOwner, parseBody, readJsonObject, recordError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { z } from 'zod';
import { fuse, pack } from '../lib/loreIndex';
import { WORD_SIMILARITY_THRESHOLD, wordSimilarity } from '../lib/trigram';
import { normalised } from '../lib/worldKeys';
import { prisma } from './db';
import {
  chunksById,
  firstPassages,
  forgetRecords,
  indexedVersions,
  indexRecords,
  type LoreRecord,
  type LoreStore,
  loreStore,
  LoreUnavailable,
  namesInScope,
  RANK_DEPTH,
  type Scope,
  storeEmbeddings,
  textRanked,
  vectorRanked,
  waiting,
} from './loreStore';
import { WORLD_ENTITY_KINDS, type WorldEntityKind } from './worldEntities';
import { matchedEntities } from './worldEntityRoute';

export const EMBED_BATCH = 16;

type Embed = (texts: string[]) => Promise<number[][]>;
let registered: { embed: Embed; model: string } | undefined;

/** The composing app's embedder (texts in, 768-wide vectors out; the wiki adds the task prefixes). */
export function registerLoreEmbedder(embed: Embed, model: string): void {
  registered = { embed, model };
}

function embedder(): { embed: Embed; model: string } | undefined {
  if (registered !== undefined) return registered;
  const url = process.env.WIKI_EMBED_URL;
  const model = process.env.WIKI_EMBED_MODEL;
  if (!url || !model) return undefined;
  return {
    model,
    embed: async (texts) => {
      const answer = await fetch(`${url.replace(/\/$/, '')}/embeddings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model, input: texts }) });
      if (!answer.ok) throw new Error(`the embedder answered ${answer.status}`);
      const body = (await answer.json()) as { data: { index: number; embedding: number[] }[] };
      return [...body.data].sort((one, two) => one.index - two.index).map((row) => row.embedding);
    },
  };
}

const SELECT = { id: true, name: true, description: true, entry: true, campaignId: true, settingId: true, kind: true, source: true, updatedAt: true } as const;
type Row = LoreRecord & { updatedAt: Date };

function delegate(kind: WorldEntityKind): { findMany: (args: object) => Promise<unknown[]> } {
  switch (kind) {
    case 'location':
      return prisma.location as never;
    case 'person':
      return prisma.person as never;
    case 'faction':
      return prisma.faction as never;
    case 'item':
      return prisma.item as never;
    case 'journal':
      return prisma.journal as never;
  }
}

/** The index brought up to the owner's records: the changed cut again, the gone forgotten. */
export async function syncLore(store: LoreStore, ownerId: string): Promise<void> {
  const live = { createdById: ownerId, deletedAt: null, OR: [{ isTemplate: null }, { isTemplate: false }] };
  for (const kind of WORLD_ENTITY_KINDS) {
    const versions = (await delegate(kind).findMany({ where: live, select: { id: true, updatedAt: true } })) as { id: string; updatedAt: Date }[];
    const held = indexedVersions(store, kind);
    const current = new Map(versions.map((row) => [row.id, row.updatedAt.toISOString()]));
    const changed = versions.filter((row) => held.get(row.id) !== current.get(row.id)).map((row) => row.id);
    const gone = [...held.keys()].filter((id) => !current.has(id));
    if (gone.length > 0) forgetRecords(store, gone);
    for (let start = 0; start < changed.length; start += 500) {
      const rows = (await delegate(kind).findMany({ where: { id: { in: changed.slice(start, start + 500) } }, select: SELECT })) as Row[];
      indexRecords(store, kind, rows.map((row) => ({ ...row, version: row.updatedAt.toISOString() })));
    }
  }
}

let embedding = false;

/** Waiting passages embedded, a batch at a time, one request in flight; quiet when there's nothing to do. */
export async function embedWaiting(store: LoreStore, pauseMs = 250): Promise<number> {
  const found = embedder();
  if (embedding || found === undefined || store.vectorProblem !== null) return 0;
  embedding = true;
  let done = 0;
  try {
    for (;;) {
      const batch = waiting(store, EMBED_BATCH);
      if (batch.length === 0) break;
      const vectors = await found.embed(batch.map((row) => `search_document: ${row.name}: ${row.text}`));
      storeEmbeddings(store, found.model, batch.map((row, index) => ({ id: row.id, vector: vectors[index] ?? [] })));
      done += batch.length;
      await new Promise((resolve) => setTimeout(resolve, pauseMs));
    }
  } finally {
    embedding = false;
  }
  return done;
}

const loreSearchBody = z.object({
  text: z.string().min(1).max(20000),
  k: z.number().int().min(1).max(100).default(20),
  token_budget: z.number().int().min(1).max(50000).default(2000),
  kinds: z.array(z.enum(WORLD_ENTITY_KINDS as unknown as [WorldEntityKind, ...WorldEntityKind[]])).optional(),
  tags: z.array(z.string()).optional(),
  include_setting: z.boolean().default(true),
});

export async function campaignLoreSearchPost(request: NextRequest, context: { params: Promise<Record<string, string>> }): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const campaignId = (await context.params).id ?? '';
    const input = parseBody(loreSearchBody, await readJsonObject(request), 'lore_search');
    const campaign = await prisma.campaign.findFirst({ where: { id: campaignId, createdById: owner.id }, select: { id: true, settingId: true, scenarioId: true } });
    if (campaign === null) throw recordError(404, 'CampaignModel not found');
    const store = await loreStore().catch((error: unknown) => {
      throw error instanceof LoreUnavailable ? recordError(503, error.message) : error;
    });
    await syncLore(store, owner.id);
    const scope: Scope = {
      owners: [campaign.id, ...(campaign.scenarioId ? [campaign.scenarioId] : [])],
      settingId: input.include_setting ? (campaign.settingId ?? null) : null,
      gameSystemId: null,
      ...(input.kinds === undefined ? {} : { kinds: input.kinds }),
    };
    const methods: Record<string, string> = {};
    const rankings: Record<string, string[]> = {};

    const { shown } = await matchedEntities(owner.id, campaignId, input.text, input.include_setting, input.tags ?? [], input.k);
    const first = firstPassages(store, scope, shown.map((entity) => entity.id));
    const exact = shown.map((entity) => first.get(entity.id)).filter((id): id is string => id !== undefined);
    methods.exact = 'used';

    const words = [...new Set(normalised(input.text).split(' ').filter((word) => word.length > 2))];
    rankings.text = textRanked(store, scope, words);
    methods.text = 'used (FTS5)';
    rankings.trigram = namesInScope(store, scope)
      .map((row) => ({ id: row.id, score: wordSimilarity(row.name, input.text) }))
      .filter((row) => row.score >= WORD_SIMILARITY_THRESHOLD)
      .sort((one, two) => two.score - one.score || (one.id < two.id ? -1 : 1))
      .slice(0, RANK_DEPTH)
      .map((row) => row.id);
    methods.trigram = 'used (word similarity, in process)';

    const found = embedder();
    if (store.vectorProblem !== null) methods.vector = `unavailable: ${store.vectorProblem}`;
    else if (found === undefined) methods.vector = 'unavailable: no embedder (registerLoreEmbedder, or WIKI_EMBED_URL and WIKI_EMBED_MODEL)';
    else {
      try {
        const [vector] = await found.embed([`search_query: ${input.text}`]);
        rankings.vector = vectorRanked(store, scope, vector ?? []);
        methods.vector = 'used';
      } catch (error) {
        methods.vector = `unavailable: the embedder failed (${error instanceof Error ? error.message : String(error)})`;
      }
    }

    const fused = fuse(rankings, exact);
    const ranks = Object.fromEntries(Object.entries({ exact, ...rankings }).map(([name, ids]) => [name, new Map(ids.map((id, index) => [id, index + 1]))]));
    const rows = chunksById(store, fused.slice(0, input.k * 3).map(([id]) => id));
    const ordered = fused
      .filter(([id]) => rows.has(id))
      .map(([id, score]) => {
        const row = rows.get(id)!;
        return {
          id,
          record_id: row.target_entity_id,
          record_type: row.target_entity_type,
          name: row.name,
          path: JSON.parse(row.path) as string[],
          text: row.text,
          tokens: row.tokens,
          source: row.source,
          page: row.page,
          score,
          ranks: Object.fromEntries(Object.entries(ranks).flatMap(([name, held]) => (held.has(id) ? [[name, held.get(id)!]] : []))),
        };
      });
    const passages = pack(ordered, input.token_budget).slice(0, input.k);
    void embedWaiting(store).catch(() => undefined);
    return NextResponse.json({ passages, methods });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
