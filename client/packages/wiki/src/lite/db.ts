// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The Prisma client the wiki's lite routes use: the app's own, handed in once by `wikiLite({ prisma })`
 * (its generated client, whose schema carries the wiki's fragment, prisma/wiki.prisma). The package
 * never makes a client of its own, so one app keeps one connection.
 */
import type { PrismaClient } from '@prisma/client';

let client: PrismaClient | undefined;

export function bindPrisma(given: PrismaClient): void {
  client = given;
}

function bound(): PrismaClient {
  if (client === undefined) throw new Error('@zephyrex-rpg/wiki/lite: call wikiLite({ prisma }) before its routes answer');
  return client;
}

/** The bound client: every property read goes to the app's client. */
export const prisma: PrismaClient = new Proxy({} as PrismaClient, {
  get: (_target, key) => Reflect.get(bound(), key),
});
