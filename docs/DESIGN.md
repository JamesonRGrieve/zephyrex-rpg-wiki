# zephyrex-rpg-wiki: design

A worldbuilding and campaign wiki that competes with Kanka and World Anvil. It is the
world's record: who, where, when, what happened and what is secret. The VTT and the AI
product build on it. Suite context and ownership: [zephyrex-rpg-ai: docs/SUITE.md](https://github.com/JamesonRGrieve/zephyrex-rpg-ai/blob/main/docs/SUITE.md). Entity
fields: [OBJECT_PLAN](../server/OBJECT_PLAN.md) §4 (Tier 0 `entity_posts` and Tier 1
`world_*`), §7 (cross-cutting) and §8 (World Anvil templates).

## Who it is for

- **The GM / worldbuilder**: builds the world between sessions, keeps secrets, writes
  session reports.
- **The player**: reads what their character knows, keeps their own journal, follows the
  timeline.
- **The writer**: uses it with no game at all, for manuscripts, lore and a series bible.

## Principles

1. **Writing first.** The editor is the product. Linking an entity is as fast as typing its
   name (`@`), and reading a page feels like a well-set book, not a database form.
2. **Structure without forms.** Every World Anvil template is an entity *kind* with a
   prompted outline (OBJECT_PLAN decision 3). You fill only the prompts you care about, and
   property kits add structured fields on demand.
3. **Secrets are first-class.** Visibility is per entity, per post, per attribute and per
   inline block, all through `acl_rbac` (§7). "View as player X" shows exactly what that
   player sees.
4. **Everything connects.** Every entity can link to every other with a typed relation,
   and every link shows on both ends.
5. **Yours to take away.** Full import from Kanka and World Anvil, export to Markdown, JSON
   and the adapter formats (§7). No lock-in, and that is a selling point against both
   incumbents.

## Feature parity matrix: full parity

**The target is full feature parity with Kanka and World Anvil** (operator, 2026-11-20):
every feature either product offers is planned here. Nothing is left out of scope.

Sources:

- Kanka: its API, audited in OBJECT_PLAN §1, plus its features page and release notes
  (v3.0 custom modules, v3.5 whiteboards, 2025).
- World Anvil: its feature and learn pages and its pricing page (2026-11).

Rows marked *(verify)* are known from the product but not yet confirmed against a current
page. Every row is re-checked in `docs/research/competitors.md` before launch. "Lite" is the
self-hosted single-user build.

| # | Feature | Seen in | Lite | SaaS |
|---|---|---|---|---|
| **Entities** |
| W1 | All entity kinds: characters, locations, organisations, families, items, events, quests, journals, notes, races, creatures, abilities, the full World Anvil template set as kinds | both | ✓ | ✓ |
| W2 | Rich-text entry (Plate): headings, tables, images, embeds, `@` mentions with hover cards | both | ✓ | ✓ |
| W3 | Posts: pinnable notes on any entity, each with its own visibility | Kanka | ✓ | ✓ |
| W4 | Properties and property kits: typed attributes (text, number, checkbox, section, star rating, random), templates | Kanka | ✓ | ✓ |
| W5 | Typed relations with attitude, colour, mirror; relation explorer | Kanka | ✓ | ✓ |
| W6 | Tags (hierarchical), statuses, categories | Kanka | ✓ | ✓ |
| W7 | Entity templates: start a new entity from a template entity | Kanka | ✓ | ✓ |
| W8 | Inventory on any entity | Kanka | ✓ | ✓ |
| **Secrets and access** |
| W9 | Per-entity, per-post, per-attribute visibility; roles | Kanka | ✓ (one user plus "view as") | ✓ |
| W10 | Inline secret blocks visible to chosen roles or players | World Anvil | ✓ | ✓ |
| W11 | "View as" a role or player | Kanka | ✓ | ✓ |
| **Time** |
| W12 | Custom calendars: months, weekdays, leap rules, moons, seasons, eras, intercalary days | both | ✓ | ✓ |
| W13 | Timelines with eras; drag to place | both | ✓ | ✓ |
| W14 | Chronicles: the timeline drives the map to each event's place | World Anvil | ✓ | ✓ |
| W15 | Reminders on calendar dates | Kanka | ✓ | ✓ |
| **Places** |
| W16 | Location hierarchy at every scale, from star system to room | both | ✓ | ✓ |
| W17 | Maps from an image or a VTT-published render: layers, groups, pins linked to entities, zoom, real-world maps | Kanka | ✓ | ✓ |
| **People and powers** |
| W18 | Family trees (dagre DAG), with private lineage | World Anvil | ✓ | ✓ |
| W19 | Diplomacy webs (force-directed faction relations) | World Anvil | ✓ | ✓ |
| W20 | Organisation hierarchy and membership (role, rank, status) | Kanka | ✓ | ✓ |
| **Story** |
| W21 | Quests and hooks as a DAG with elements | Kanka | ✓ | ✓ |
| W22 | Plots: acts, beats, twists | World Anvil | ✓ | ✓ |
| W23 | Manuscripts: chapters, scenes, word count, focus mode | World Anvil | ✓ | ✓ |
| W24 | Session reports, linked to everything they mention | World Anvil | ✓ | ✓ |
| W25 | Statblocks embedded in articles, rendered from VTT system data when present | World Anvil | ✓ | ✓ |
| **Publishing and sharing** |
| W26 | Campaign dashboard: configurable widgets (recent, pinned, calendar, random) | Kanka | ✓ | ✓ |
| W27 | Public world pages: read-only, themed, SEO-friendly | World Anvil | – | ✓ |
| W28 | Members, invitations, roles; applications to join | Kanka | – | ✓ |
| W29 | Per-world theme (palette, fonts, header art) from tokens, not raw CSS | World Anvil (CSS) | ✓ | ✓ |
| W30 | Gallery and asset library | Kanka | ✓ | ✓ (with cloud storage quotas) |
| **Data** |
| W31 | Import from Kanka (API) and World Anvil (export); export to Markdown, JSON, Foundry journals | — | ✓ | ✓ |
| W32 | Full-text search across the world, with ACL-aware results | both | ✓ | ✓ |
| W33 | Revision history and restore on every entity | World Anvil | ✓ | ✓ |
| W34 | Installable app, offline reading | — | ✓ | ✓ |
| **Parity additions** |
| W35 | Whiteboards: a free canvas of shapes, notes, and live entity and map cards | Kanka (3.5), World Anvil | ✓ | ✓ |
| W36 | Custom entity types (Kanka "custom modules"): name, icon, fields; any module can be disabled or renamed per campaign | Kanka | ✓ | ✓ |
| W37 | Webhooks on entity changes (Discord and any URL) | Kanka | ✓ | ✓ |
| W38 | Discord integration: post updates, look up entities from a bot | Kanka (webhooks), World Anvil *(verify)* | – | ✓ |
| W39 | Vanity URLs for public worlds | Kanka | – | ✓ |
| W40 | Readers: followers and paid subscriber tiers on a public world; subscriber-only blocks inside public articles | World Anvil | – | ✓ |
| W41 | Co-authors with shared manuscripts; drag secrets into writing notes | World Anvil | – | ✓ |
| W42 | Community statblock library: share, copy and edit statblocks | World Anvil | – | ✓ |
| W43 | VTT integration: push statblocks and journals to a table (our VTT; Foundry through the adapter) | World Anvil (Foundry) | ✓ | ✓ |
| W44 | Embeds: HeroForge and other 3D models, video, audio, any oEmbed source | World Anvil | ✓ | ✓ |
| W45 | Custom CSS per world (scoped to the world's pages and sanitised), alongside the token themes of W29 | World Anvil, Kanka *(verify)* | ✓ | ✓ |
| W46 | Community: a public world directory, follows, comments, worldbuilding challenges and prompts | World Anvil | – | ✓ |
| W47 | Plugin marketplace: themes, sheet templates, content packs | Kanka *(verify)* | ✓ (install from file) | ✓ |
| W48 | Files attached to any entity, with per-plan limits | Kanka | ✓ | ✓ |
| W49 | Entity map polygons and areas (not only pins) | Kanka (1.42) | ✓ | ✓ |
| W50 | Calendar weather per date | Kanka | ✓ | ✓ |
| W51 | Campaign brief and frame on the campaign page, when the AI product's campaign frame is loaded (premise, tone, truths, boundaries; GM secrets withheld) | ours | ✓ | ✓ |
| W52 | Scenarios drafted from the world (plots, quests, factions, places), and a scenario's outcome written back as events, journal entries and changed relations | ours | ✓ | ✓ |

OBJECT_PLAN decision 28 (whiteboards out of scope, "pure frontend") is superseded by the
operator's full-parity direction. W35 needs a `whiteboard` model in the wiki (board,
elements, entity links), recorded in OBJECT_PLAN when that phase starts.

## Screens

| Path | What it is |
|---|---|
| `/` | Landing: hero showing a live sample world page, Kanka/World Anvil comparison, import promise, pricing, FAQ. |
| `/w` | Your worlds and campaigns. |
| `/w/[world]` | The campaign dashboard (W26). |
| `/w/[world]/[kind]` | An entity list per kind: cards or a table, filters (tag, status, location), a tree view for hierarchical kinds. |
| `/w/[world]/[kind]/[id]` | **The entity page** (the kind is in the path: each kind has its own table, OBJECT_PLAN; S1, 2026-11-20). Header art and portrait, title, kind, tags. Then the entry, posts (pinned first), properties, relations, inventory, mentions-of-this, and a "seen in" list (sessions, timelines, maps). Edit in place. |
| `/w/[world]/map/[id]` | Map viewer: pins, layers, groups, search a pin, open an entity in a side sheet. |
| `/w/[world]/timeline/[id]` | Timeline editor and viewer; `?chronicle` fuses it with a map (W14). |
| `/w/[world]/calendar/[id]` | Fantasy calendar: month grid, moons, seasons, events, reminders. |
| `/w/[world]/graph` | Relations: family tree or diplomacy web, filterable by kind. |
| `/w/[world]/write/[id]` | Manuscript focus mode (W23). |
| `/w/[world]/settings` | Members, roles, theme, import/export, calendar defaults. |
| `/p/[world]/…` | Public pages (SaaS, W27). |

### Key interactions

- **`@` mention:** type `@` and the start of a name, pick from a typeahead across every
  kind. If nothing matches, Enter creates a stub entity of the chosen kind without leaving
  the sentence.
- **Secret block:** select text and choose *Secret* → pick roles or players. It renders with
  a subtle side rule for those who can see it, and is absent from the HTML for those who
  cannot (enforced on the server, never by hiding with CSS).
- **View as:** a switch in the header re-renders the page as a chosen player sees it.
- **Command palette (⌘K):** go to any entity, create any kind, run import/export.

## Visual design

Editorial. A reading measure of about 70 characters, a serif display face for titles and a
humanist sans for UI. Header art bleeds full width behind the title, with a scrim for
contrast. Each entity kind has a lucide icon and a token colour (the entity type registry,
OBJECT_PLAN §9), used on chips, pins and graph nodes. Per-world themes (W29) swap only the
token palette and the two faces, so every theme stays accessible. Light and dark are both
first-class. A parchment-warm light theme is the default for reading.

## Data and contract

- The server extensions are `entity_posts` and `world_*` (OBJECT_PLAN §3 Tiers 0–1), with
  map authoring moved to the VTT ([zephyrex-rpg-ai: docs/SUITE.md](https://github.com/JamesonRGrieve/zephyrex-rpg-ai/blob/main/docs/SUITE.md)), plus campaigns from `rpg_core`
  and `rpg_log` (the campaign's event history, written by the VTT and the AI GM, shown as a
  filterable log beside session reports).
- Framework reuse: `genealogy` (family trees), `calendar`, `media`, `maps` (real-world tiles),
  `conversations` (Kanka conversations), `acl_rbac`, `meta_labels`, `fileio`, `wiki`
  (its `PRV_Kanka` is the import path for W31).
- The API is the framework's REST shape: `{ <resource> }` envelopes, ETag and `If-Match` on
  every write, `412` with `current` when stale, `428` without it, plus GraphQL via zod2gql.
- **What the AI product needs from the wiki:**
  - entity read and search under the caller's ACL;
  - "what does character X know" (visibility-filtered reads as that player);
  - writes of journal entries and session reports;
  - lorebook generation sources (`ai_lorebook.source_entity_*`).
  These are the wiki's ordinary endpoints. The AI product adds nothing to the wiki's schema.

### Decided (operator, 2026-11-20)

- **Dependencies point one way: rpg_core → world_\*.** Tier 1 (`world_spatial`, `world_social`,
  `world_inventory`, `world_narrative`) stays campaign-free. `rpg_core` scopes its records to a
  campaign by injecting `campaign_id` onto them with `@extension_model`, as it injects `kind`,
  `campaign_id`, `user_id`, `location_id` and `entry` onto genealogy's Person. Each `*_id` names its
  model, so the framework gives it a real foreign key. (OBJECT_PLAN's §3 and §7 otherwise made
  `world_spatial` and `rpg_core` depend on each other.)
- **Per-entity property values (W4)** live in the framework's `metadata` key-value store, keyed by
  `target_entity_type` and `target_entity_id` (a polymorphic target the framework gains for this;
  operator, 2026-11-21). Property kits (`world_taxonomy`) are the templates.
- **Tags (W6) are `world_taxonomy`'s own taxa**, not the framework's `meta_labels` (flat kebab ids
  with no kind or campaign); Kanka's tags are display names in a tree.
- **Relations (W5) are genealogy's relationships**, widened by `world_social` with organisation
  endpoints, a colour and a mirror; attitude is genealogy's `intensity` (-1 to +1).
- **An entry is a Plate value** (decision 16), stored as JSON text, with its plain-text copy kept as
  the record's `description` for search. Both back ends derive it by one rule, held to
  `contract/entry-text-cases.json`. An `@` mention is an inline node carrying
  `target_entity_type` and `target_entity_id`, never a name.
- **Kinds are enums in `contract/wiki.json`**, which the server and the client both read.
- **The wiki owns `rpg_core`** (campaigns, and the Person and Tier 1 injections) and the world
  tables; zephyrex-vtt loads these extensions from a pinned commit of this repo and deletes its
  own copies. Rule systems (`game_systems`, and `game_system_id` on campaigns and items) are the
  VTT's `rpg_systems`, since the wiki depends on no other suite product.
- **A record's world is fixed once set** (Zephyrex RPG, for rpg-ai's A15 sync): changing
  `campaign_id` away from a world is refused (422); moving is copy and delete.
- **Every wiki extension ships its own Alembic migrations**, and rpg_core's adds its injected
  columns to other extensions' tables with real foreign keys.

### Database-level guarantees

What the database enforces, and what only the BLL does (a 422) until it can:

- Unique pairs are unique indexes: a taxon once per record, one status per record, one progress
  row per actor and hook, one hook dependency per pair.
- One endpoint a side on a relation (a person or an organisation, never both) is the BLL's rule
  only. The CHECK waits for genealogy's existing rows to be cleaned: a row with neither person end
  would fail it, and SQLite adds a CHECK by rebuilding the table (Zephyrex RPG, 2026-11-21).

## Campaigns, frames and scenarios

The wiki owns campaigns. The AI product owns how a campaign is framed and its scenarios are
modeled (zephyrex-rpg-ai `docs/DESIGN.md`, *Campaign framing* and *Scenario modeling*). With
both loaded:

- a campaign's page shows its brief, and the setting truths the frame lists are wiki entities
  (W51);
- a scenario can be drafted from the wiki's plots, quests, factions and places, and its cast
  and places link to wiki entities;
- a scenario's outcome is written back: events on the timeline, a session report, changed
  relations and dispositions (W52), under the wiki's ACL like any other write.

The wiki adds no schema for this. It is the AI product reading and writing the wiki's own
records.

## Editions

- **Lite:** one person, every authoring feature, SQLite, local files for media. "View as"
  stands in for real players.
- **SaaS:** members and roles, public pages, cloud media with quotas, sync, revision
  retention by plan.

## Progress

| Slice | What | State |
|---|---|---|
| S1 | Worlds (`rpg_core` campaigns), places (`world_spatial`), people (genealogy + `rpg_core`); `/w` screens; lite twin | Committed (b677f97); all green since the framework's validator fix (f734b0df) |
| S2 | Organisations and families (`world_social`), items and inventory (`world_inventory`, W8), worn vs packed (`associated_person_id`), every extension's migrations | Committed (65248fa) |
| S2b | rpg-ai A15: world_entities (a world's changes since a time, tombstones included), the summary rule, a record's world fixed once set, lite soft delete | Done, on the framework's changes() (a4d6a3ec); committed with S3 |
| S3 | Journals, notes, lore and session reports (`world_narrative`; rpg-ai A24's session_report and session_report_get), posts (`entity_posts`, W3) | Done: both editions, server 51/51 and client checks on 58137; committed with S2b |
| S3b | The plot-hook DAG in `world_narrative` (hooks, hook_dependencies with a cycle guard, person_hooks, faction_hooks; OBJECT_PLAN §6, moved from vtt's rpg_state), rpg_core's campaign on hooks; hooks kept out of world_entities (GM secrets until W9) | Done: both editions, server 57/57 and client checks on 58137 |
| S4a | Tags, categories, races and statuses (`world_taxonomy`, W6); relations between people and organisations with attitude, colour and mirror (`world_social` on genealogy's relationships, W5) | Done in both editions; server 61/62 on 58137, the one red waiting on the framework's status/statuses fix |
| S4b | Property kits and values (W4, on the framework's metadata with a polymorphic target), templates (W7) | Waits on that framework change |
| S2c | Pictures: the framework's new attachments extension (an asset over storage, a polymorphic attachment with role primary_image) on any record; world_entities.picture (rpg-ai A31) | Waits on the framework's new attachments extension (operator's choice, 2026-11-21) |
| S5 | Cross-kind search, the mention editor (W2), Kanka import | Not started |

## Phases

1. Entity core (W1–W8), mention editor, entity page, lists, search. Import from Kanka.
2. Secrets and access (W9–W11), relations graph (W18–W20).
3. Time (W12–W15) and maps (W16–W17, W14).
4. Story (W21–W25), dashboard, public pages, members.
5. World Anvil import, export adapters, offline reading.
6. Parity additions: whiteboards, custom entity types, webhooks and Discord, embeds and
   custom CSS (W35–W50). Then the SaaS community layer: readers and subscriber tiers,
   co-authors, statblock library, world directory, marketplace.

Ported back from the AI product's build: the shared UI shell, the entity type registry,
mention hover cards and the lore drawer ([zephyrex-rpg-ai: docs/DESIGN.md](https://github.com/JamesonRGrieve/zephyrex-rpg-ai/blob/main/docs/DESIGN.md)).

## Proposed, not confirmed

Ideas this product proposes beyond the operator's confirmed scope above. **None is built until the
operator confirms it.** Size: S (days), M (one to two weeks), L (more). Requested 2026-11-20 for the
operator's review.

| # | Idea | Why it helps | Size | Depends on |
|---|---|---|---|---|
| WP1 | Contradiction finder | AI flags facts that disagree across pages (dates, family, who died), each with links to both | M | The AI product, W12, W18 |
| WP2 | What a player knows | The wiki as one player has seen it so far, from visibility and session reports; a GM's prep check | M | W9, W11, W24 |
| WP3 | Names in a culture's style | A name generator that matches the style of the names a culture already has in the world | S | The AI product |
| WP4 | Backlinks and orphans | Automatic "mentioned in" lists on every page and a report of pages nothing links to | S | W2 |
| WP5 | Printable campaign book | Chosen pages laid out as a PDF sourcebook in the world's theme | M | W27, W29 |
| WP6 | Pages unlocked by play | A player-facing wiki whose pages open as the campaign reaches beats, so it never spoils | M | W9, A60 |
| WP7 | Name pronunciation | A spoken sample stored with each name, so the table says it the same way | S | A29 |
| WP8 | Import Obsidian, Notion and Markdown | Bring an existing notes vault in, links and folders kept | M | W31 |
