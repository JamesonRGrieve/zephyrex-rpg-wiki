# @zephyrex-rpg/wiki

The pages of Zephyrex RPG Wiki, with the components, data hooks and shared rules they are made
of, for an app that composes the wiki: rpg-ai's Together mode, where one server runs the wiki's
extensions beside the app's own. The wiki's own client uses the same pages.

## What an app needs

**The server** loads the wiki's extensions in this order (`server/rpg_wiki_app.py`):

```
auth_session, genealogy, cloud, attachments, metadata, world_spatial, world_social,
world_inventory, world_narrative, world_taxonomy, world_properties, entity_posts, rpg_core
```

The first five are server-framework's; the rest are in the wiki's `server/extensions`, with
`wiki_shared` (a plain package, no manifest) importable from the same path and the repository's
`contract/` beside `server/`. A deployment configures a cloud provider for attachments
(`CLOUD_LOCAL_DIRECTORY` for a directory on disk). Leave `rpg_log` out.

**The client** installs this package from the wiki checkout at its pinned commit, built:

```bash
cd zephyrex-rpg-wiki/client/packages/wiki && node scripts/compile.mjs && node scripts/verify-dist.mjs
```

then, in the app:

```jsonc
// package.json
"@zephyrex-rpg/wiki": "file:../../zephyrex-rpg-wiki/client/packages/wiki"
```

```css
/* the app's stylesheet: Tailwind emits only the classes it finds */
@source '../node_modules/@zephyrex-rpg/wiki/dist';
```

```ts
// zephyrex.config.ts
import { wikiExtension } from '@zephyrex-rpg/wiki/extension';

extensions: [wikiExtension(), /* … */];
```

`wikiExtension({ base })` mounts the pages under `base` (`w` by default): the worlds at `/w`, a
world's records at `/w/:world/:kind`, a record at `/w/:world/:kind/:id`, and `/w/:world/taxonomy`
and `/w/:world/plot`, with a "Worlds" menu entry. Each section shows only when `GET /v1/extension`
lists the extension that serves it, so the same pages run on any edition.

Peers: `zephyrex` (at the framework pins the wiki builds on), `next`, `react`, `swr`, `zod` and
`lucide-react`.

## What it exports

Subpaths of `dist/`: `extension` (`wikiExtension`), `base` (`useWikiBase`, `WikiBaseProvider`),
`pages/*` (`WorldsPage`, `KindPage`, `RecordPage`, `TaxonomyPage`, `PlotPage`, each taking its route's
values as props), `components/world/*`, `features/*` (capabilities and the data hooks) and `lib/*`
(the rules both back ends share: requirements, dispositions, names, entries, kits, slugs, summaries).

## License

AGPL-3.0-or-later.

## The lite API (`@zephyrex-rpg/wiki/lite`)

An app that never serves it (a hosted edition, whose server composes the wiki's extensions) builds
the package without it: `node scripts/compile.mjs --no-lite`. The lite API types against
`@zephyrex/lite` and a Prisma client generated with the wiki's models, which such an app lacks.

An app's lite edition (Next.js only, no server-framework) serves the wiki's API itself:

1. Copy the schema fragment into a Prisma multi-file schema folder, beside the app's own datasource
   and generator, and keep it current with `--check` in the app's tests:

   ```bash
   node node_modules/@zephyrex-rpg/wiki/scripts/prisma-fragment.mjs prisma/schema [--check]
   ```

2. Generate the app's migration from its composed schema (`prisma migrate diff`); the wiki ships no
   migrations, since history belongs to each database.
3. Mount the routes behind one catch-all, `app/api/v1/[...wiki]/route.lite.ts`:

   ```ts
   import { wikiLite } from '@zephyrex-rpg/wiki/lite';
   import { prisma } from '~/lib/prisma';

   export const { GET, POST, PUT, PATCH, DELETE } = wikiLite({ prisma });
   ```

   The app's own specific routes answer first. Its `GET /v1/extension` lists
   `WIKI_LITE_EXTENSIONS` beside its own.
