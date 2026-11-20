# zephyrex-rpg-wiki

A worldbuilding and campaign wiki built on the Zephyrex framework: entities, lore,
secrets, relations, timelines, calendars, maps and the campaign's history. It is planned
for full feature parity with Kanka and World Anvil.

It is one of three products in the Zephyrex RPG suite:

- **zephyrex-rpg-wiki**: the world.
- [zephyrex-vtt](https://github.com/JamesonRGrieve/zephyrex-vtt): the table.
- [zephyrex-rpg-ai](https://github.com/JamesonRGrieve/zephyrex-rpg-ai): AI characters and
  an AI game master.

The wiki depends on neither of the others. Both build on it.

Status: early alpha. The design is in [docs/DESIGN.md](docs/DESIGN.md), and the shared
entity model for the whole suite is in [server/OBJECT_PLAN.md](server/OBJECT_PLAN.md).

## Layout

```
server/   FastAPI backend, a consumer of the zephyrex Python package
client/   Next.js frontend, a consumer of the zephyrex npm package
docs/     DESIGN.md
```

## Server extensions

| Extension | Depends on  | Provides |
|-----------|-------------|----------|
| `rpg_log` | `rpg_state` | Event log: encounters, combat, dialogue, interactions, transactions |

**Interim dependency.** `rpg_log` still references `rpg_state` models (campaign,
location, item instance, trait), and `rpg_state` now lives in zephyrex-vtt. Until
OBJECT_PLAN §6 moves campaigns, locations and items into this repo and turns the trait
link into a polymorphic reference, `rpg_log` loads only alongside zephyrex-vtt's
extensions.

## Running

```bash
cd server && pip install -e ".[dev]" && python app.py     # API on :2000
cd client && pnpm install && pnpm dev                       # UI on :1109
```

The client depends on the framework packages checked out as siblings (`../client-framework`,
`../auth`, `../zod2gql`, `../dynamic-form`) through `file:` paths.

## License

[AGPL-3.0-or-later](./server/LICENSE)
