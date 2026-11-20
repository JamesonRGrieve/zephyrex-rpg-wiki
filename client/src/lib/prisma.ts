// SPDX-License-Identifier: AGPL-3.0-or-later
import { PrismaBetterSqlite3 } from '@prisma/adapter-better-sqlite3';
import { PrismaClient } from '@prisma/client';

// Prisma 7 connects through a driver adapter rather than a bundled query engine.
const adapter = new PrismaBetterSqlite3({ url: process.env.DATABASE_URL ?? 'file:./rpg_wiki.db' });

// One client across hot reloads in development (each `new PrismaClient` opens its own connection).
const globalForPrisma = globalThis as typeof globalThis & { prisma?: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient({ adapter });

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}
