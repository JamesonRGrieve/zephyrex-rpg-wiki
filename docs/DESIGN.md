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
| W38 | Discord integration: post updates, look up entities from a bot | Kanka (webhooks), World Anvil (Discord webhooks) | – | ✓ |
| W39 | Vanity URLs for public worlds | Kanka | – | ✓ |
| W40 | Readers: followers and paid subscriber tiers on a public world; subscriber-only blocks inside public articles | World Anvil | – | ✓ |
| W41 | Co-authors with shared manuscripts; drag secrets into writing notes | World Anvil | – | ✓ |
| W42 | Community statblock library: share, copy and edit statblocks | World Anvil | – | ✓ |
| W43 | VTT integration: push statblocks and journals to a table (our VTT; Foundry through the adapter) | World Anvil (Foundry) | ✓ | ✓ |
| W44 | Embeds: HeroForge and other 3D models, video, audio, any oEmbed source | World Anvil | ✓ | ✓ |
| W45 | Custom CSS per world (scoped to the world's pages and sanitised), alongside the token themes of W29 | World Anvil (world, per-article and container CSS), Kanka (premium CSS) | ✓ | ✓ |
| W46 | Community: a public world directory, follows, comments, worldbuilding challenges and prompts | World Anvil | – | ✓ |
| W47 | Plugin marketplace: themes, sheet templates, content packs | Kanka (plugins.kanka.io) | ✓ (install from file) | ✓ |
| W48 | Files attached to any entity, with per-plan limits | Kanka | ✓ | ✓ |
| W49 | Entity map polygons and areas (not only pins) | Kanka (1.42) | ✓ | ✓ |
| W50 | Calendar weather per date | Kanka | ✓ | ✓ |
| W51 | Campaign brief and frame on the campaign page, when the AI product's campaign frame is loaded (premise, tone, truths, boundaries; GM secrets withheld) | ours | ✓ | ✓ |
| W52 | Scenarios drafted from the world (plots, quests, factions, places), and a scenario's outcome written back as events, journal entries and changed relations | ours | ✓ | ✓ |
| W53 | Archive: hide a record from lists without deleting it | Kanka | ✓ | ✓ |
| W54 | CSV import | Kanka | ✓ | ✓ |
| W55 | Relations between any kinds of record | both | ✓ | ✓ |
| W56 | Dispositions: how a person regards the party, a person or an organisation, changing as hooks resolve; relation influences | ours (dh-campaign) | ✓ | ✓ |
| W57 | Hook requirements as all/any expressions (with game-system checks VTT evaluates), blocked-with-excuse, resolution in a session; a plot board | ours (dh-campaign) | ✓ | ✓ |
| W58 | Rollable random tables and random generators, linking to records | World Anvil | ✓ | ✓ |
| W59 | Content trees (organograms): hierarchies, magic systems, ranks | World Anvil | ✓ | ✓ |
| W60 | Notebook: quick notes outside any record, colour-coded, mobile-first | World Anvil | ✓ | ✓ |
| W61 | To-do list, filled with drafts and mention stubs (records named before they exist) | World Anvil | ✓ | ✓ |
| W62 | Autolinker: suggest mentions for names already in the world, accept all or one by one | World Anvil | ✓ | ✓ |
| W63 | Variables: values set once and used across records | World Anvil | ✓ | ✓ |
| W64 | Public-world extras: custom domain and slugs, SEO metadata, RSS feed, announcements, side navigation, homepage layout, password-protected pages, access codes | World Anvil | – | ✓ |

## Feature audit against Kanka and World Anvil (2026-11-21)

The operator asked for a full feature audit against the competitors before the initial release
(2026-11-21, via Zephyrex RPG); the wiki's targets are Kanka and World Anvil. Each feature is
marked against what is **built and on `main`** (9486e7c), not what is planned:

- **Covered:** built in both editions, with its tests (where).
- **Partial:** some of it is built (what's missing).
- **Planned:** not built; its W-row above holds it.
- **Not planned:** a deliberate no (why).
- **Out of scope:** the competitor's business, not a product feature.

**Release:** ● is needed for the initial release, which is DESIGN's phase 1: the entity core,
the mention editor, the entity page, lists, search and Kanka import. ○ is a later phase.

**Sources.** Kanka: its features, pricing and docs pages, its API overview, and the release posts
3.5 to 3.15 (Nov 2025 to Aug 2026), read on 2026-11-20 and 21. World Anvil: its features index,
all 16 feature pages, the per-tier feature list (learn/account/list-features) and the changelog,
read on 2026-11-21 in the operator's own Chromium (SOP *STL Library Archival → Browser for store
reads*; World Anvil refuses automated and headless reads with HTTP 403).

| Area | Feature | Kanka | World Anvil | Wiki | Where / what's missing | Release |
|---|---|---|---|---|---|---|
| **Entities** | Worlds (campaigns) | ✓ | ✓ | Covered | `rpg_core` campaigns; `/w` | ● |
| | Places, nested at every scale, with kinds | ✓ | ✓ | Covered | `world_spatial`; tree view (S1) | ● |
| | People (characters), kind, place, world | ✓ | ✓ | Covered | genealogy + `rpg_core` (S1) | ● |
| | Life status (alive, dead, missing), title | ✓ (3.10) | ✓ | Partial | statuses (S4a) can carry it; no title field | ● |
| | Organisations and families, tree, defunct | ✓ | ✓ | Partial | `world_social` (S2); no defunct flag | ● |
| | Organisation membership (role, rank) | ✓ | ✓ | Partial | relations `member_of` (S4a); no members table or rank (W20) | ○ |
| | Items: kind, quantity, durability, creators, price, weight | ✓ | ✓ | Partial | `world_inventory` (S2); price, weight, size, creators missing (W4 properties can hold them) | ● |
| | Journals, notes, lore, handouts, manuscripts | ✓ | ✓ | Covered | `world_narrative` journals (S3) | ● |
| | Session reports linked to what they mention | ✓ (journals) | ✓ | Covered | `session_report` (S3, rpg-ai A24) | ● |
| | Quests with status and elements | ✓ | ✓ | Partial | hooks DAG with per-actor progress (S3b), hook state and resolution (S3c); no quest elements | ● |
| | Events (with places, reminders) | ✓ | ✓ | Planned | W1, W12–W15 | ○ |
| | Races, species, creatures, cultures, religions | ✓ | ✓ | Partial | taxa of those kinds (S4a); no creature/race pages of their own | ○ |
| | Abilities (with charges) | ✓ | – | Planned | W1 | ○ |
| | Calendars | ✓ | ✓ | Planned | W12 | ○ |
| | Timelines and eras | ✓ | ✓ | Planned | W13 | ○ |
| | Maps | ✓ | ✓ | Planned | W17, reusing VTT's renderer (below) | ○ |
| | World Anvil's 25+ prompted article templates as kinds | – | ✓ | Partial | kinds per type from the contract; no prompted template fields | ○ |
| | Custom entity types (Kanka custom categories; WA custom templates) | ✓ premium | ✓ paid | Planned | W36 | ○ |
| | Disable or rename a module per world | ✓ | – | Partial | capabilities hide what isn't loaded; no per-world toggle or rename | ○ |
| | Archive (hide from lists, keep) | ✓ (3.5) | – | Planned | W53; soft delete exists for sync, not archive | ○ |
| | Aliases (search and mentions) | ✓ | – | Planned | rpg-ai's sync carries `aliases: []`; no field yet | ● |
| **Entity page** | Rich-text entry (stored Plate value) | ✓ | ✓ (BBCode) | Partial | stored and shown (S1); **no editor**: pages are read-only | ● |
| | Edit fields in place | ✓ | ✓ | **Not built** | lists create by name and kind and delete; record pages can't edit anything | ● |
| | `@` mentions | ✓ | ✓ | Partial | mention nodes in the data model (S3); no editor, no hover cards (W2) | ● |
| | Backlinks ("mentioned in") | ✓ | ✓ | Planned | W2; Kanka counts map markers too | ● |
| | Posts / articles on any entity, pinned | ✓ | ✓ | Covered | `entity_posts` (S3); read-only | ● |
| | Properties (attributes) and property kits | ✓ | ✓ | Planned | S4b, waiting on the framework's metadata target (W4) | ● |
| | Entity templates (archetypes) | ✓ | ✓ | Planned | S4b (W7) | ○ |
| | Inventory on any entity, worn vs packed | ✓ | ✓ | Covered | S2 (W8); read-only on the page | ● |
| | Tags (tree, colour, icon), statuses, categories | ✓ | ✓ | Covered | `world_taxonomy` (S4a); no icon field | ● |
| | Portrait, header image, gallery picker | ✓ | ✓ | Planned | S2c, on the framework's attachments extension | ● |
| | Files attached to an entity | ✓ | ✓ | Planned | S2c / W48 | ○ |
| | Sidebar / profile summary (pinned properties) | ✓ | ✓ | Planned | with W4 | ○ |
| | Revision history and restore | ✓ (90 days) | ✓ | Planned | W33 | ○ |
| | Deleted-entry recovery (30 days) | ✓ premium | – | Partial | lite tombstones (S2b) exist; no restore UI | ○ |
| **Relations** | Typed relations, attitude, colour, mirror | ✓ | ✓ | Covered | world_social on genealogy (S4a); read-only list | ● |
| | Relations between any kinds (not only people and organisations) | ✓ | ✓ | Partial | people and organisations only; any kind is W55 | ○ |
| | Relation explorer / web, PNG export | ✓ | ✓ | Planned | W5, W19 | ○ |
| | Family trees | ✓ premium | ✓ | Planned | W18 (genealogy has the data) | ○ |
| | Diplomacy webs | – | ✓ | Planned | W19 | ○ |
| | Dispositions that change with events | – | – | Covered | W56, S3c: dispositions and relation influences (person page, relations) | ○ |
| **Story** | Plot-hook DAG, progress per person and organisation | ✓ (quests) | ✓ (plots) | Covered | S3b | ● |
| | Requirements as all/any expressions, blocked-with-excuse, resolution | – | – | Covered | W57, S3c: requirements, resolution, plot board, `plot_state` | ○ |
| | Plots: acts, beats, twists | – | ✓ | Planned | W22 | ○ |
| | Manuscripts: chapters, word count, focus mode | – | ✓ paid | Partial | journal kinds `manuscript`, `chapter`, `prose`; no writing tools (W23) | ○ |
| | Statblocks and character sheets | ✓ (plugin sheets) | ✓ | Planned | W25, from VTT's systems | ○ |
| | Whiteboards | ✓ premium | ✓ | Planned | W35 | ○ |
| **Time** | Calendars, moons, seasons, weather, reminders | ✓ | ✓ | Planned | W12, W15, W50 | ○ |
| | Timelines, eras, chronicles on a map | ✓ | ✓ | Planned | W13, W14 | ○ |
| **Maps** | Image maps with pins linked to entities | ✓ | ✓ | Planned | W17; reuse VTT's renderer | ○ |
| | Layers, groups, polygons, paths with distance, custom icons | ✓ (Maps v4) | ✓ paid | Planned | W17, W49 | ○ |
| | Live multi-user editing and presence | ✓ (3.14) | – | Planned | framework live_sync | ○ |
| | Real-world maps | ✓ *(verify)* | – | Planned | W17 | ○ |
| **Access** | Per-entity, per-post, per-property visibility; roles | ✓ | ✓ | Planned | W9; `acl_rbac` is optional and unwired | ○ |
| | Inline secrets for chosen readers | – | ✓ paid | Planned | W10 | ○ |
| | View as a player | ✓ | ✓ | Planned | W11 | ○ |
| | Members, invitations, roles, join requests | ✓ | ✓ | Planned | W28 (SaaS) | ○ |
| | Co-authors | – | ✓ paid | Planned | W41 | ○ |
| **Campaign** | Dashboard with widgets, several per role | ✓ | ✓ | Planned | W26 | ○ |
| | Bookmarks / quick links, quick create | ✓ | – | Planned | with W26; ⌘K command palette in Screens | ○ |
| | Players' characters per campaign | ✓ | ✓ | Partial | person `kind` and `user_id` (S1); no player screens | ○ |
| | Dice rolls, conversations | deprecated | – | Out of scope | Kanka deprecated both; VTT owns dice | — |
| **Find** | Search across every kind, full text, with filters | ✓ (Ctrl+K) | ✓ | Partial | find-by-name on each list only (W32, S5) | ● |
| | Filters on lists (tag any/all, negation, status, place) | ✓ | ✓ | Partial | API filters exist (S1–S4a); no filter UI beyond name | ● |
| **Data** | Export JSON and Markdown | ✓ | ✓ (JSON zip) | Planned | W31 | ● |
| | Import from Kanka | ✓ (own JSON) | – | Planned | W31, phase 1 | ● |
| | Import from World Anvil | – | – | Planned | W31, phase 5 | ○ |
| | CSV import | ✓ (3.9) | – | Planned | W54 | ○ |
| | Public API | ✓ | ✓ (Boromir, approved keys) | Partial | SaaS: the framework's REST and GraphQL at `/v1`; lite: the same REST; no docs page or tokens UI | ○ |
| | Webhooks, Discord | ✓ premium | ✓ (Discord webhooks, Master) | Planned | W37, W38 (framework `webhooks`) | ○ |
| | Sync to an AI product's lorebook | – | – | Covered | `world_entities` (S2b, rpg-ai A15) | ● |
| | Foundry / VTT journals | – | ✓ (community module) | Planned | W43, through VTT | ○ |
| **Publishing** | Public worlds and pages | ✓ | ✓ | Planned | W27 (SaaS) | ○ |
| | Themes, custom CSS, theme builder | ✓ premium | ✓ | Partial | light and dark from the framework tokens (fixed in the audit); W29, W45 | ○ |
| | Vanity URLs, white label | – | ✓ (Sage) | Planned | W39; white label not planned | ○ |
| | Followers, paid subscribers, subscriber groups | – | ✓ paid | Planned | W40 (SaaS) | ○ |
| | Community: showcase, comments, challenges | ✓ (showcase) | ✓ | Planned | W46 (SaaS) | ○ |
| | Plugins / marketplace (sheets, themes, packs) | ✓ premium | – | Planned | W47 | ○ |
| **Tools** | Rollable random tables and generators | – | ✓ | Planned | W58 | ○ |
| | Content trees (organograms) | – | ✓ | Planned | W59 | ○ |
| | Notebook for quick notes | – | ✓ | Planned | W60 | ○ |
| | To-do list with drafts and mention stubs | – | ✓ | Planned | W61 | ○ |
| | Autolinker for existing names | – | ✓ | Planned | W62 | ○ |
| | Variables reused across records | – | ✓ | Planned | W63 | ○ |
| | Public-world extras (domains, slugs, SEO, RSS, announcements, passwords, access codes) | – | ✓ paid | Planned | W64 | ○ |
| **Platform** | Mobile web: works at 360–390 px, 44 px targets | responsive | ✓ (mobile notebook) | Covered | audited on phone and tablet (9486e7c) | ● |
| | Installable app, offline reading | – | – | Planned | W34 | ○ |
| | Self-hosted, one person, free | – | – | Covered | the lite edition | ● |
| | Live multi-user presence | ✓ (maps, whiteboards) | – | Planned | framework live_sync | ○ |
| | Ads, referrals, achievements, hall of fame, tiers and storage quotas | ✓ | ✓ | Out of scope | business model; quotas come with SaaS billing | — |

**Maps reuse VTT's renderer.** Map rendering belongs to the VTT, which is taking a
mobile-optimised renderer and Universal VTT and Foundry scene import. The wiki's map (W17) is a
world map with pins, layers, groups and areas linked to wiki records. It should reuse from VTT:
the renderer component (tiled image, pan and zoom, touch), its layer and group model, and the
scene importer as a way in, and add only the wiki's pins (target type and id), areas (W49) and
the record side sheet. A VTT scene published to the wiki is a map variant, as dh-campaign's
`maps:` block already treats exterior and interior variants.

**Counts** (90 rows, after S3c and the World Anvil reading): Covered 15, Partial 18, Not built 1, Planned 54, Out of scope 2. **Every
Planned and Partial row is in scope for the initial release** (operator's goal: full coverage,
2026-11-21, via Zephyrex RPG); ● marks phase 1, which orders the work and drops nothing. **The gaps that matter for the initial release** (● and not Covered): editing a
record in place, the entry editor with `@` mentions, backlinks and aliases, properties (S4b),
portraits and images (S2c), cross-kind search and list filters, Kanka import and JSON/Markdown
export, life status and item fields (with properties), quest status and elements, and
organisation details.

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

- **Settings above campaigns (S6; rpg-ai DESIGN "Settings and systems", the operator,
  2026-11-21).** A setting (Warhammer 40,000, Fallout, Modern…) encloses campaigns; every world
  record can name its setting, and one with a setting and no campaign is that setting's canon:
  what anyone in it would know. A campaign's records belong to its campaign's setting, and a
  record's setting, like its world, is fixed once set. `canon_level` (common, learned, secret) is
  stored but left unset until the operator decides whether red canon notices use it. VTT's game
  systems reference settings; mechanics stay VTT's.

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

Framing and scenarios are the AI product reading and writing the wiki's own records; the wiki's
own part since the play tests is in *Play-test rulings* below (a scenario is a campaign copied on
start).

## Play-test rulings (operator, 2026-11-21)

Decisions from the operator's play tests of rpg-ai on the composed suite, as the wiki implements
them (rpg-ai `docs/DESIGN.md`, *Play-test rulings*, has the AI side). Each holds in both editions.

- **Copy on start.** A scenario (`campaigns.is_scenario`) is a campaign play never edits. Starting
  it (`instantiate_campaign`, `POST /v1/campaign/{id}/instantiate`) makes a playthrough: a new
  campaign (`scenario_id` names its scenario) with its own copy of every record and every link
  between them, each reference (and each id inside an entry or a requirement) turned to its copy,
  and an id map back to the caller. The setting's canon is never copied: it stays shared and
  read-only to play. Templates stay with the scenario; hooks start unresolved. vault_import makes
  every campaign it imports a scenario. Lists filter `?is_scenario=true` and `?scenario_id=`.
- **Starting positions.** A person's `location_id` in the scenario is where they start; the copy
  takes it, then play moves them. Openings tell the player where they are; they never ask.
- **Provenance.** Campaigns and every record say where they came from: `provenance` homebrew,
  official or adapted, and a `source` (title, publisher, product or page). Official scenarios are
  parsed in for personal use; their entities carry the same mark.
- **Play-style tags.** Campaigns take taxons of kind `play_style`. Eight shared ones are seeded as
  the system's (freeform, combat-heavy, narrative, mystery, exploration, social, horror,
  dungeon-crawl); anyone adds their own. A framing note's tags are its campaign's play styles.
- **GM-only records.** A record whose private "GM only" property is true (the vault's
  `is_private: true`) is `gm_only` in world_entities and campaign_documents: it reaches the GM
  and narrator, never a player's prompt.
- **Pictures.** A record's picture is an uploaded asset or an https link (fandom, wikis…), the link
  first; links are shown with no referrer. vault_import takes a same-name image beside a note, or
  `image:`/`picture:`; st_import takes a card's image or icon link.
- **Campaign documents.** `campaign_documents` gives each record's full text, journals first,
  `gm_only` marked: rpg-ai's data bank.
- **Presence and the world tick.** World entities carry a person's `location_id` and a place's
  `parent_id`, so a scene knows who is present. A person has a `routine` (slots from and to HH:MM on
  days, at a place, doing something) and `motivations`; a campaign has a clock (`campaign_clock`,
  `advance_clock`; day 1, 08:00 to start). The GM side moves people (`move_person`, `POST
  /v1/person_move`), within their campaign or its setting's canon, and each move is kept with where
  from, when in-world and why. rpg-ai writes none of these tables itself: it calls these abilities
  as the campaign's GM.
- **Compendium and SRD import.** `compendium_import` brings the official setting material in as
  setting-wide canon, provenance official with book and page: the D&D 5e SRD (CC-BY-4.0, with its
  attribution) into the dnd setting from the dnd5e Foundry system's packs (6.0.5), then the wh40k-rpg
  system's printed-book records into warhammer-40000, de-duplicated across lines, DH2 first. A
  record's `compendium_source` is its Foundry compendium UUID, which VTT's rules packs key by too.
  (Approved; next after the importers batch.)
- **Narrative character building.** The wiki owns the person, the story half of any character: a
  guided New character page (concept, appearance, personality, background, goals and fears,
  relationships, voice, picture), the setting's canon offered as suggestions and never enforced,
  archetypes from templates, and a hand-off to VTT's RAW builder and back. (Planned; after the
  importers.)
- **Batched importers.** Imports and copies write a record type at a time through plural creates
  (server-framework a5121fa8 runs each entity's hooks; at most 100 a create), never one request per entity.

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
| S3c | Narrative state from the operator's dh-campaign tracker (W56, W57): hook requirements as all/any expressions with game-system checks (their hooks become the edges), excuse, resolution in a session; `plot_state` (ability) and a plot board; dispositions (party, person or organisation; scale plus nuances; changed by a hook) and relation influences, in `world_narrative` | Done in both editions; server 76/77 on 58137 (the one red is the framework's status bug), client checks and audit green |
| S6 | Settings (rpg-ai DESIGN b73eb13, the operator, 2026-11-21): a setting encloses campaigns; its campaign-less records are its canon, read by rpg-ai's canon notices (`setting_canon`, `world_entities(include_setting)`); `canon_level` stored, unset until decided; VTT's game systems name a setting | Built in both editions (no UI); the operator's open questions: setting as the top level of /w, canon_level, where a published setting's canon comes from |
| S6b | Setting slugs and the seeded settings (VTT's game systems name settings by slug, operator-confirmed via VTT, 2026-11-21): `slug` unique, derived from the name when not given (numbered past any taken), fixed once set (contract/wiki.json setting_slug, contract/slug-cases.json); the contract's `seed_settings` (Warhammer 40,000, Age of Sigmar, Warhammer Fantasy, D&D, Fallout, Modern) are the system's: everyone reads them, only the system changes them | Built in both editions (rpg_core 006, lite 20261121060000_s6b) |
| S4a | Tags, categories, races and statuses (`world_taxonomy`, W6); relations between people and organisations with attitude, colour and mirror (`world_social` on genealogy's relationships, W5) | Done in both editions; server 61/62 on 58137, the one red waiting on the framework's status/statuses fix |
| S4b | Properties (W4: a record's own key/values, the framework's `/v1/record_metadata`), property kits (`world_properties`: keys with types and defaults; apply adds the keys a record lacks), templates (W7: `is_template` on the six kinds, fixed at creation; `/v1/template/instantiate` copies fields, entry, properties and tags; never in world_entities or setting_canon) | Server done; lite: templates, kits and record properties (the properties panel works in lite); next: lite kit apply and template instantiate, then the kit picker and New from template |
| S2c | Pictures and files: the framework's attachments extension (an asset over cloud storage, a polymorphic attachment with a role from contract/wiki.json attachment_roles) on any record; world_entities.picture (rpg-ai A31) | Server done (uploads, and pictures by link first); pictures by link in both editions with a picture panel; next: lite uploads and the gallery (@zephyrex/attachments' AttachmentGallery) |
| S4c–S4d | Aliases, keywords and the AI voice (with SillyTavern's prompt parts); a lorebook activation block on every record | Done in both editions |
| S7 | The pages as the `@zephyrex-rpg/wiki` package (`wikiExtension`, `lib/paths`), and its lite API as `@zephyrex-rpg/wiki/lite` (one catch-all, a Prisma fragment); VTT and rpg-ai compose it | Done |
| Imports | vault_import (Obsidian vaults: kinds, pictures, provenance, play styles, scenarios) and st_import (SillyTavern cards and World Info) | Done; batching next |
| Rulings | Everything in *Play-test rulings* above but the compendium import, the character builder and batching | Done in both editions (main 0885ba1 and after) |
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
