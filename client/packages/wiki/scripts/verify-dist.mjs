#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-or-later
/** Imports every module in dist/ under plain Node, as client-framework's verify:dist does: a missing
 * extension, a path into the repository or an unresolvable package fails here, not in a consumer. */
import { readdirSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DIST = resolve(dirname(fileURLToPath(import.meta.url)), '../dist');
const files = (directory) =>
  readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
const modules = files(DIST).filter((path) => path.endsWith('.js'));
let failed = 0;
for (const module of modules) {
  try {
    await import(pathToFileURL(module).href);
  } catch (error) {
    failed += 1;
    console.error(`${module}: ${error instanceof Error ? error.message : String(error)}`);
  }
}
console.log(`${modules.length - failed} of ${modules.length} modules load`);
process.exit(failed === 0 ? 0 : 1);
