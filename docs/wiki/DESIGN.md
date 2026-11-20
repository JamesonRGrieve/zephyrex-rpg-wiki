# zephyrex-rpg-wiki: design

A worldbuilding and campaign wiki that competes with Kanka and World Anvil. It is the
world's record: who, where, when, what happened and what is secret. The VTT and the AI
product build on it. Suite context and ownership: [../SUITE.md](../SUITE.md). Entity
fields: [OBJECT_PLAN](../../server/OBJECT_PLAN.md) §4 (Tier 0 `entity_posts` and Tier 1
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
| `/w/[world]/e/[id]` | **The entity page.** Header art and portrait, title, kind, tags. Then the entry, posts (pinned first), properties, relations, inventory, mentions-of-this, and a "seen in" list (sessions, timelines, maps). Edit in place. |
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
  map authoring moved to the VTT ([../SUITE.md](../SUITE.md)), plus campaigns from `rpg_core`
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

## Editions

- **Lite:** one person, every authoring feature, SQLite, local files for media. "View as"
  stands in for real players.
- **SaaS:** members and roles, public pages, cloud media with quotas, sync, revision
  retention by plan.

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
mention hover cards and the lore drawer ([../ai/DESIGN.md](../ai/DESIGN.md)).
