# zephyrex-rpg-wiki

A worldbuilding and campaign wiki for tabletop games: places, people, organisations, items, lore,
plot hooks and session reports, kept per setting and per campaign.

It is the world half of the Zephyrex RPG suite. [zephyrex-vtt](https://github.com/JamesonRGrieve/zephyrex-vtt)
is the table (scenes, tokens, sheets) and [zephyrex-rpg-ai](https://github.com/JamesonRGrieve/zephyrex-rpg-ai)
adds AI characters and an AI game master. The wiki depends on neither. Both build on it, and when
they run together they share its server extensions, its database and its pages.

The aim is feature parity with Kanka and World Anvil. [docs/DESIGN.md](docs/DESIGN.md) has the
design, the rulings behind it and what is built so far.

## Contents

- [What it does](#what-it-does)
- [Editions](#editions)
- [Requirements](#requirements)
- [Setup](#setup)
- [Running](#running)
- [Importing a world](#importing-a-world)
- [Development](#development)
- [Layout](#layout)
- [Documentation](#documentation)
- [Status](#status)
- [Licence](#licence)

## What it does

A **setting** is a universe. Its records with no campaign are its canon, which every campaign in
it can read. A **campaign** is one group's game in a setting, with its own records on top. A fresh
instance has one setting, Reality; you make the rest.

Each setting and campaign holds six kinds of record:

| Kind | Examples |
|---|---|
| Places | A star system, a city, a building, a room, each inside the one above |
| People | Player characters, NPCs, creatures, vehicles |
| Organisations | Guilds, families, churches, armies |
| Items | Weapons, documents, anything carried |
| Journals | Session reports, diaries, lore, handouts |
| Hooks | Quests, mysteries and rumours, with what each one needs first |

Around them:

- tags, categories, races and statuses, in a tree, on any record;
- relations between people and organisations, with an attitude, and dispositions a hook can change;
- a plot board that sorts hooks into ready, blocked, waiting on a roll and done;
- properties on any record, and property kits that add a set of them at once;
- scenarios, which are campaigns you start: the wiki copies one into a fresh playthrough;
- eras inside a setting, so a campaign sees only its own period's canon;
- an origin on everything (homebrew, official or adapted, with its source);
- each person's voice for the AI (SillyTavern's parts) and a TTS voice;
- importers for Obsidian vaults, SillyTavern cards and World Info, and Foundry compendiums.

## Editions

The same pages run on two back ends. A page never asks which one it is on: it reads
`GET /v1/extension` and shows a feature when the extension that serves it is listed.

| | Lite | SaaS |
|---|---|---|
| Back end | the Next.js app's own API routes | `server/` on server-framework |
| Database | SQLite, through Prisma | Postgres (SQLite in tests) |
| People | one person, no sign-in | accounts and teams |
| Lore search | FTS5 and sqlite-vec | Postgres full text, pg_trgm and pgvector |

## Requirements

- Node 24 and pnpm 10
- Python 3.11 and [uv](https://docs.astral.sh/uv/) (SaaS edition only)
- git, to fetch the framework checkouts

The client and server build against the Zephyrex frameworks at the commits
[deploy/frameworks.env](deploy/frameworks.env) pins: server-framework, client-framework, auth,
dynamic-form and zod2gql. They are checked out beside this repository, not installed from a
registry.

## Setup

The scripts lay out a separate build workspace: a copy of this repository with each framework
beside it at its pinned commit. Point them at a new directory, never the one this checkout is in,
since the copy replaces `<workspace>/zephyrex-rpg-wiki`.

```bash
deploy/fetch-frameworks.sh ~/zx-wiki        # copy this repo, clone each framework at its pin
deploy/compile-frameworks.sh ~/zx-wiki      # build the client frameworks' packages
cd ~/zx-wiki/zephyrex-rpg-wiki/client && pnpm install
cd ../server && uv sync
```

If you already keep the frameworks checked out beside this repository at those commits, skip the
scripts and install in place.

## Running

Lite, the app on its own:

```bash
cd client
pnpm dev                    # http://localhost:1109
```

SaaS, the server and the app:

```bash
cd server && .venv/bin/python rpg_wiki_app.py                 # API on :2000
cd client && NEXT_PUBLIC_RPG_WIKI_VARIANT=saas pnpm dev        # UI on :1109
```

| Variable | Where | Meaning |
|---|---|---|
| `NEXT_PUBLIC_RPG_WIKI_VARIANT` | client | `saas` for the hosted build with accounts; anything else is lite |
| `RPG_WIKI_SERVER_URI` | client, SaaS | The server the app proxies `/api` to (default `http://127.0.0.1:2000`) |
| `DATABASE_URL` | client, lite | The SQLite file, e.g. `file:./lite.db` |
| `WIKI_EMBED_URL`, `WIKI_EMBED_MODEL`, `WIKI_EMBED_KEY` | both | The embedding service for lore search (optional; full-text search works without it) |
| `WIKI_EMBED_BACKFILL_HOURS` | server | When the full embedding backlog may run, server-local hours (default `1-7`) |

The server applies its migrations when it starts. Open `/w` for the settings and their campaigns.

## Importing a world

Every importer runs from `server/`, has `--dry-run`, and goes through the wiki's own routes, so a
second run changes only what differs. The setting must exist first (`POST /v1/setting`).

```bash
cd server
.venv/bin/python -m vault_import ~/vaults/harbour --setting reality --dry-run --base-url http://localhost:2000
.venv/bin/python -m st_import --card mara.png --campaign "Harbour Lights" --setting reality --dry-run --base-url http://localhost:2000
```

| Command | Reads |
|---|---|
| `vault_import` | Obsidian vaults: one record per note with an `entity_type` in its frontmatter |
| `st_import` | SillyTavern character cards (V2/V3, PNG or JSON) and World Info |
| `compendium_import` | A Foundry VTT system's compendium packs, into a setting's canon |
| `book_import` | Transcribed books into the lore index (in process, private instances only) |
| `scenario_repair` | Scenarios that can't be played, and what would mend them |

Use `--lite` for a lite edition's API, `WIKI_TOKEN` for a SaaS server, or `--app module:factory
--owner USER_ID` to run in process. The note format and the rest are in the Storybook guide's
*Importing* chapter.

## Development

```bash
cd server && .venv/bin/python -m pytest extensions    # server tests
cd client && pnpm typecheck                            # types
cd client && pnpm test                                 # unit tests (Vitest)
cd client && pnpm storybook                            # stories and docs on :6006
cd client && pnpm storybook-build && pnpm storybook-test   # every story's play test
cd client && pnpm exec playwright test                 # lite edition end to end
```

Every component has a Storybook story with a `play` test, and an accessibility violation fails it.
Pages run against a mock back end (`client/packages/wiki/src/testing/wiki.mocks.ts`).

A rule both back ends apply is written once in Python and once in TypeScript, and both are tested
against the same cases in [contract/](contract). Change the cases first.

## Layout

```
server/
  extensions/           world_spatial, world_social, world_inventory, world_narrative,
                        world_taxonomy, world_properties, entity_posts, rpg_core; wiki_shared
  rpg_wiki_app.py       the app and its extension order
  vault_import/ …       the importers
client/
  packages/wiki/        @zephyrex-rpg/wiki: pages, components, data hooks, the lite API, the docs
  src/                  the wiki's own app
  e2e/                  Playwright specs and the visual audit
contract/               wiki.json and the shared rules' cases
deploy/                 the framework pins and the scripts that fetch and build them
docs/DESIGN.md          design, rulings and progress
```

## Documentation

- **The Storybook** (`pnpm storybook`) has the user guide (*Wiki/Guide*: settings, campaigns and
  scenarios, records, tags and relations, the plot board, importing, troubleshooting) and the
  developer pages (*Wiki/Developers*: architecture, both editions, rpg_core's abilities, the
  contract, composing the wiki, testing), beside every component's stories.
- [client/packages/wiki/README.md](client/packages/wiki/README.md) is for an app that composes
  the wiki: the server's extension order, installing the package, and its lite API.
- [docs/DESIGN.md](docs/DESIGN.md) and [server/OBJECT_PLAN.md](server/OBJECT_PLAN.md) hold the
  design and the suite's shared entity model.

## Status

Early alpha. Records, settings and campaigns, scenarios, the plot board, taxonomy, relations,
properties, pictures by link, the AI voice and lore search are built in both editions. Cross-kind
search, the mention editor, secrets per player, maps and timelines are not built yet;
[docs/DESIGN.md](docs/DESIGN.md) has the full list.

## Licence

[AGPL-3.0-or-later](server/LICENSE).
