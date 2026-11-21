#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Builds @zephyrex-rpg/wiki's dist/ (S7c). The contract (contract/*.json at the repository root) is
 * the one source both back ends read; the package takes a copy of it here, never committed:
 * src/ is staged into build/ with the contract beside it, compiled to dist/, and each emitted
 * import is made loadable by Node: relative imports get their .js, the contract's JSON its import
 * attribute, and Next's subpaths (no exports map) their file name.
 *
 * --no-lite leaves out the lite API (src/lite.ts, src/lite/): an app that never mounts it (vtt
 * hosted) has neither @zephyrex/lite nor a Prisma client generated with the wiki's models, which
 * the lite API types against. Pages and libraries never import it, so the rest builds without it.
 */
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const PACKAGE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPOSITORY = resolve(PACKAGE, '../../..');
const BUILD = join(PACKAGE, 'build');
const DIST = join(PACKAGE, 'dist');
const CONTRACT_IMPORT = "'../../../../contract/wiki.json'";

rmSync(BUILD, { recursive: true, force: true });
rmSync(DIST, { recursive: true, force: true });
cpSync(join(PACKAGE, 'src'), BUILD, { recursive: true });
if (process.argv.includes('--no-lite')) {
  rmSync(join(BUILD, 'lite.ts'));
  rmSync(join(BUILD, 'lite'), { recursive: true });
}
mkdirSync(join(BUILD, 'contract'), { recursive: true });
for (const name of readdirSync(join(REPOSITORY, 'contract'))) {
  if (name.endsWith('.json')) cpSync(join(REPOSITORY, 'contract', name), join(BUILD, 'contract', name));
}
const contractSource = join(BUILD, 'contract.ts');
const staged = readFileSync(contractSource, 'utf8');
if (!staged.includes(CONTRACT_IMPORT)) throw new Error(`contract.ts no longer imports ${CONTRACT_IMPORT}`);
writeFileSync(contractSource, staged.replace(CONTRACT_IMPORT, "'./contract/wiki.json'"));

execFileSync(join(PACKAGE, '../../node_modules/.bin/tsc'), ['-p', join(PACKAGE, 'tsconfig.compile.json')], { stdio: 'inherit' });

const NEXT_SUBPATHS = ['next/image', 'next/link', 'next/navigation', 'next/server'];
const files = (directory) =>
  readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
for (const file of files(DIST).filter((path) => path.endsWith('.js') || path.endsWith('.d.ts'))) {
  const text = readFileSync(file, 'utf8');
  const fixed = text.replace(/(from\s+|import\s*\(\s*)'([^']+)'/g, (whole, lead, specifier) => {
    if (NEXT_SUBPATHS.includes(specifier)) return `${lead}'${specifier}.js'`;
    if (!specifier.startsWith('.')) return whole;
    if (specifier.endsWith('.json')) return file.endsWith('.js') ? `${lead}'${specifier}' with { type: 'json' }` : whole;
    const base = resolve(dirname(file), specifier);
    if (existsSync(`${base}.js`) || existsSync(`${base}.d.ts`)) return `${lead}'${specifier}.js'`;
    if (existsSync(join(base, 'index.js'))) return `${lead}'${specifier}/index.js'`;
    return whole;
  });
  if (fixed !== text) writeFileSync(file, fixed);
}
rmSync(BUILD, { recursive: true, force: true });
console.log(`built ${files(DIST).length} files into dist/`);
