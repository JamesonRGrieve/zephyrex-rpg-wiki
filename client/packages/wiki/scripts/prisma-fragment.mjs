#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Copies the wiki's Prisma schema fragment (prisma/wiki.prisma: its lite records) into an app's
 * multi-file schema folder, or with --check fails when the app's copy differs from this package's.
 *
 *   node node_modules/@zephyrex-rpg/wiki/scripts/prisma-fragment.mjs prisma/schema [--check]
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const check = args.includes('--check');
const folder = args.find((arg) => !arg.startsWith('--'));
if (folder === undefined) {
  console.error('usage: prisma-fragment.mjs <prisma schema folder> [--check]');
  process.exit(2);
}
const fragment = readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'prisma', 'wiki.prisma'), 'utf8');
const target = join(resolve(folder), 'wiki.prisma');
if (check) {
  if (!existsSync(target) || readFileSync(target, 'utf8') !== fragment) {
    console.error(`${target} differs from @zephyrex-rpg/wiki's prisma/wiki.prisma: run prisma-fragment.mjs ${folder}, then generate a migration`);
    process.exit(1);
  }
  console.log(`${target} matches @zephyrex-rpg/wiki`);
} else {
  writeFileSync(target, fragment);
  console.log(`wrote ${target}`);
}
