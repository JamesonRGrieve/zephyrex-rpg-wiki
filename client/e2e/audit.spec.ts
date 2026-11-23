// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * The visual audit (UX and UI standard: a screenshot audit before each UX release): every page of
 * the lite edition at desktop 1366, tablet 768@2x and phone 390@2x, dark and light, first on an empty database
 * (the first-run states) and then on a seeded world (e2e/support/seed.ts).
 *
 * Every shot is checked for what a person would notice without looking closely: no sideways
 * overflow, no page errors, nothing fetched from another host, no same-origin link that answers
 * 4xx or 5xx, exactly one h1, headings that never skip a level, a title, and every image named.
 * With VISUAL_AUDIT=<dir> it also saves each screenshot and what the page reported beside it,
 * for the review image by image:
 *
 *   VISUAL_AUDIT=<dir> playwright test e2e/audit.spec.ts
 *
 * (zephyrex-rpg-ai's e2e/audit.spec.ts, whose checks this keeps as they are.)
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { devices, expect, test, type Browser, type Page, type TestInfo } from '@playwright/test';
import { seedWorld, type Seeded } from './support/seed';

const AUDIT_DIR = process.env.VISUAL_AUDIT ?? '';
// Real devices (their user agents, touch and mobile behaviour), at the audit's sizes.
const VIEWPORTS = {
  desktop: { ...devices['Desktop Chrome'], viewport: { width: 1366, height: 768 }, deviceScaleFactor: 1 },
  phone: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 },
  tablet: { ...devices['iPad Mini'], viewport: { width: 768, height: 1024 }, deviceScaleFactor: 2 },
} as const;
const THEMES = ['dark', 'light'] as const;
/** The dev server's own badge is not part of the app: leave it out of the shots. */
const HIDE_DEV_TOOLS = 'nextjs-portal { display: none !important; }';
const PER_SHOT_MS = 15_000;

interface Report {
  path: string;
  title: string;
  overflow: number;
  h1: number;
  headingSkips: string[];
  unnamedImages: number;
  pageErrors: string[];
  consoleErrors: string[];
  foreignRequests: string[];
  brokenLinks: string[];
}

/** Each same-origin link's status, fetched once per URL (so once per edition) for the run. */
const linkStatus = new Map<string, Promise<number>>();

async function brokenLinks(page: Page, origin: string): Promise<string[]> {
  const hrefs = await page.evaluate(
    (here) =>
      [...document.querySelectorAll('a[href]')]
        .map((link) => new URL((link as HTMLAnchorElement).href, here))
        .filter((url) => url.origin === new URL(here).origin)
        .map((url) => `${url.origin}${url.pathname}${url.search}`),
    origin,
  );
  const broken: string[] = [];
  for (const href of new Set(hrefs)) {
    let pending = linkStatus.get(href);
    if (pending === undefined) {
      pending = page.request.get(href, { maxRedirects: 5 }).then((response) => response.status());
      linkStatus.set(href, pending);
    }
    const status = await pending;
    if (status >= 400) broken.push(`${href} (${status})`);
  }
  return broken;
}

/** Waits for what a screenshot shows to stop changing: fonts loaded, finite animations done. */
async function settled(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
  await page.evaluate(async () => {
    await document.fonts.ready;
    const finite = document
      .getAnimations()
      .filter((animation) => Number.isFinite(animation.effect?.getComputedTiming().endTime ?? Infinity));
    await Promise.all(finite.map((animation) => animation.finished.catch(() => undefined)));
  });
}

async function shoot(page: Page, origin: string, target: string, name: string): Promise<Report> {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const foreignRequests: string[] = [];
  const onPageError = (error: Error): void => void pageErrors.push(error.message);
  const onConsole = (message: { type(): string; text(): string }): void => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  };
  const onRequest = (request: { url(): string }): void => {
    const url = new URL(request.url());
    if (url.protocol.startsWith('http') && url.origin !== origin) foreignRequests.push(request.url());
  };
  page.on('pageerror', onPageError);
  page.on('console', onConsole);
  page.on('request', onRequest);
  try {
    await page.goto(target);
    await page.addStyleTag({ content: HIDE_DEV_TOOLS });
    await settled(page);
    const facts = await page.evaluate(() => ({
      title: document.title,
      // The page may scroll inside a container (the framework shell's SidebarInset), where sideways
      // overflow never widens the document: count both (16 Worldviews' finding).
      overflow: Math.max(
        document.documentElement.scrollWidth - window.innerWidth,
        ...[...document.querySelectorAll<HTMLElement>('*')]
          .filter((element) => /(auto|scroll)/.test(getComputedStyle(element).overflowY))
          .filter((element) => element.scrollHeight > element.clientHeight)
          .sort((a, b) => b.scrollHeight - a.scrollHeight)
          .slice(0, 1)
          .map((scroller) => scroller.scrollWidth - scroller.clientWidth),
      ),
      h1: document.querySelectorAll('h1').length,
      // One outline: each heading at most one level below the one before it (h2 → h4 skips).
      headingSkips: [...document.querySelectorAll('h1, h2, h3, h4, h5, h6')].flatMap((heading, index, all) => {
        const level = Number(heading.tagName[1]);
        const before = index === 0 ? 0 : Number(all[index - 1].tagName[1]);
        return level > before + 1 ? [`h${before} → h${level} "${(heading.textContent ?? '').trim().slice(0, 40)}"`] : [];
      }),
      unnamedImages: [...document.querySelectorAll('img')].filter((image) => !image.hasAttribute('alt')).length,
    }));
    const report: Report = {
      path: target,
      ...facts,
      pageErrors,
      consoleErrors,
      foreignRequests,
      brokenLinks: await brokenLinks(page, origin),
    };
    if (AUDIT_DIR !== '') {
      mkdirSync(AUDIT_DIR, { recursive: true });
      // A full-page shot sees only the document: unroll the page's own scroller (the tallest element
      // that scrolls vertically) so the shot holds the whole page, not its first screen.
      await page.evaluate(() => {
        const [scroller] = [...document.querySelectorAll<HTMLElement>('*')]
          .filter((element) => /(auto|scroll)/.test(getComputedStyle(element).overflowY))
          .filter((element) => element.scrollHeight > element.clientHeight)
          .sort((a, b) => b.scrollHeight - a.scrollHeight);
        if (scroller !== undefined) {
          scroller.style.height = 'auto';
          scroller.style.overflow = 'visible';
        }
      });
      await page.screenshot({ path: path.join(AUDIT_DIR, `${name}.png`), fullPage: true });
      writeFileSync(path.join(AUDIT_DIR, `${name}.json`), `${JSON.stringify(report, null, 2)}\n`);
    }
    return report;
  } finally {
    // Detached before the next shot, so one page's traffic never lands in another's report.
    page.off('pageerror', onPageError);
    page.off('console', onConsole);
    page.off('request', onRequest);
  }
}

function expectClean(report: Report): void {
  expect(report.overflow, `${report.path}: sideways overflow`).toBeLessThanOrEqual(0);
  expect(report.pageErrors, `${report.path}: page errors`).toEqual([]);
  expect(report.foreignRequests, `${report.path}: requests to another host`).toEqual([]);
  // A blocked script is a page that never starts (the wiki's /w, prerendered without a nonce).
  expect(
    report.consoleErrors.filter((message) => message.includes('Content Security Policy')),
    `${report.path}: blocked by the CSP`,
  ).toEqual([]);
  expect(report.brokenLinks, `${report.path}: broken links`).toEqual([]);
  expect(report.h1, `${report.path}: h1 count`).toBe(1);
  expect(report.headingSkips, `${report.path}: heading levels skipped`).toEqual([]);
  expect(report.title, `${report.path}: title`).not.toBe('');
  expect(report.unnamedImages, `${report.path}: images without alt`).toBe(0);
}

/** The pages of an empty wiki: the landing page, the worlds list, and an address that isn't a page. */
const FIRST_RUN_PAGES = ['/', '/w', '/no-such-page'];

/** The pages of a seeded world: every list, every kind's record page, and the taxonomy. */
function worldPages(seeded: Seeded): string[] {
  const w = `/w/${seeded.world}`;
  return [
    '/w',
    ...['location', 'person', 'faction', 'item', 'journal', 'hook'].map((kind) => `${w}/${kind}`),
    `${w}/about`,
    `/w/setting-${seeded.setting}/faction`,
    `${w}/location/${seeded.location}`,
    `${w}/person/${seeded.person}`,
    `${w}/faction/${seeded.faction}`,
    `${w}/item/${seeded.item}`,
    `${w}/journal/${seeded.journal}`,
    `${w}/hook/${seeded.hook}`,
    `${w}/taxonomy`,
    `${w}/taxonomy?taxon=${seeded.taxon}`,
    `${w}/plot`,
  ];
}

function slugOf(target: string): string {
  if (target === '/') return 'home';
  return target
    .slice(1)
    .replace(/\?taxon=.*/, '-taxon')
    .replaceAll('/', '-')
    .replace(/[0-9a-f]{8}-[0-9a-f-]{27}/g, 'id');
}

async function audit(browser: Browser, testInfo: TestInfo, stage: string, targets: readonly string[]): Promise<void> {
  const origin = String(testInfo.project.use.baseURL);
  for (const [size, device] of Object.entries(VIEWPORTS)) {
    for (const theme of THEMES) {
      const context = await browser.newContext({ ...device, baseURL: origin });
      await context.addCookies([{ name: 'theme', value: theme, url: origin }]);
      const page = await context.newPage();
      try {
        for (const target of targets) {
          expectClean(await shoot(page, origin, target, `${testInfo.project.name}-${stage}-${size}-${theme}-${slugOf(target)}`));
        }
      } finally {
        await context.close();
      }
    }
  }
}

/** What each seeded page must show, so a shot of an empty list never passes for a full one. */
async function expectSeedShows(page: Page, seeded: Seeded): Promise<void> {
  const w = `/w/${seeded.world}`;
  const shows: [string, string[]][] = [
    ['/w', ['The Grim Future', 'The Salt Coast', 'Warhammer 40,000']],
    // A setting's canon has the campaign's pages; a campaign shows its setting's canon, marked.
    [`/w/setting-${seeded.setting}/faction`, ['Adeptus Mechanicus']],
    [`${w}/faction`, ['Lantern Guild', 'Adeptus Mechanicus', 'Canon']],
    [`${w}/location`, ['Port Gull', 'Salt Coast']],
    [`${w}/person/${seeded.person}`, ['Lamplighters', 'Alive', 'Lantern Guild', 'Captain Ross', 'Rumour', 'guarded (cautious-neutral)', 'Since Find the lost map', '-20', 'The Lantern Keeper', 'Mira: Mind the seventh step.', 'Lantern oil', 'Three flasks']],
    [`${w}/faction/${seeded.faction}`, ['Mira of the Lantern']],
    [`${w}/about`, ['Adapted', 'Salt and Storm, Harbour Press, ch. 2', 'mystery', 'Start a playthrough']],
    [`${w}/item/${seeded.item}`, ['Official', 'Salt and Storm, Harbour Press, p. 41']],
    [`${w}/hook/${seeded.hook}`, ['Find the lost map', 'Mira of the Lantern', 'Can happen now']],
    [`${w}/plot`, ['Recover the relic', 'Hear the vox ghost', 'Rech needs the relic before he can start.', 'Find the lost map']],
    [`${w}/taxonomy?taxon=${seeded.taxon}`, ['Nobility', 'Mira of the Lantern', 'Alive']],
  ];
  for (const [target, texts] of shows) {
    await page.goto(target);
    for (const text of texts) await expect(page.getByText(text, { exact: true }).first(), `${target}: ${text}`).toBeVisible();
  }
  // The sidebar's Places, People… open the scope last shown: here the campaign, then its setting.
  await page.goto('/w/last/person');
  await expect(page).toHaveURL(new RegExp(`${w}/person$`));
  await page.goto(`/w/setting-${seeded.setting}/faction`);
  // Shown (and so remembered) before the sidebar is followed.
  await expect(page.getByText('Adeptus Mechanicus', { exact: true }).first()).toBeVisible();
  await page.goto('/w/last/journal');
  await expect(page).toHaveURL(new RegExp(`/w/setting-${seeded.setting}/journal$`));
}

test.describe.serial('visual audit', () => {
  test('first run: an empty wiki', async ({ browser }, testInfo) => {
    test.setTimeout(FIRST_RUN_PAGES.length * 6 * PER_SHOT_MS);
    await audit(browser, testInfo, 'first', FIRST_RUN_PAGES);
  });

  test('a seeded world', async ({ browser, request }, testInfo) => {
    const seeded = await seedWorld(request);
    // S6: a setting's canon read alone, and with its campaign's records (rpg-ai's canon notices).
    const canonAnswer = await request.get(`/api/v1/world_entity?setting_id=${seeded.setting}`);
    expect(canonAnswer.status(), await canonAnswer.text()).toBe(200);
    const canon = (await canonAnswer.json()) as { world_entities: { name: string; canon: boolean }[] };
    expect(canon.world_entities.map((entity) => [entity.name, entity.canon])).toEqual([['Adeptus Mechanicus', true]]);
    const both = (await (await request.get(`/api/v1/world_entity?campaign_id=${seeded.world}&include_setting=true`)).json()) as { world_entities: { name: string }[] };
    expect(both.world_entities.map((entity) => entity.name)).toContain('Adeptus Mechanicus');
    expect(both.world_entities.map((entity) => entity.name)).toContain('Port Gull');
    // S6b: the contract's seeded settings are everyone's to read and read as missing to anyone changing them; slugs are unique.
    const listed = (await (await request.get('/api/v1/setting')).json()) as { settings: { id: string; slug: string; name: string; updated_at: string }[] };
    const bySlug = new Map(listed.settings.map((one) => [one.slug, one]));
    for (const slug of ['warhammer-40000', 'age-of-sigmar', 'warhammer-fantasy', 'dnd', 'fallout', 'modern']) expect(bySlug.has(slug), slug).toBe(true);
    expect(bySlug.get('the-grim-future')?.id).toBe(seeded.setting);
    const fortyK = bySlug.get('warhammer-40000')!;
    const fixed = await request.get(`/api/v1/setting/${fortyK.id}`);
    const refused = await request.put(`/api/v1/setting/${fortyK.id}`, { data: { setting: { name: 'Mine now' } }, headers: { 'If-Match': fixed.headers().etag ?? '' } });
    expect(refused.status(), await refused.text()).toBe(404);
    const clash = await request.post('/api/v1/setting', { data: { setting: { name: 'Another Fallout', slug: 'fallout' } } });
    expect(clash.status(), await clash.text()).toBe(409);
    const numbered = await request.post('/api/v1/setting', { data: { setting: { name: 'Fallout' } } });
    expect(((await numbered.json()) as { setting: { slug: string } }).setting.slug).toBe('fallout-2');
    // S4b: a kit's keys are checked and kept as JSON text; a template never syncs.
    const kit = await request.post('/api/v1/property_kit', {
      data: { property_kit: { name: 'City', campaign_id: seeded.world, properties: [{ key: 'Population' }, { key: 'Garrison', value_type: 'number', default: 3 }] } },
    });
    expect(kit.status(), await kit.text()).toBe(201);
    expect(JSON.parse(((await kit.json()) as { property_kit: { properties: string } }).property_kit.properties)).toEqual([
      { key: 'Population', value_type: 'text', default: null, is_private: false, ordinal: 0 },
      { key: 'Garrison', value_type: 'number', default: '3', is_private: false, ordinal: 1 },
    ]);
    const twice = await request.post('/api/v1/property_kit', { data: { property_kit: { name: 'Bad', properties: [{ key: 'A' }, { key: 'A' }] } } });
    expect(twice.status(), await twice.text()).toBe(422);
    const template = await request.post('/api/v1/location', {
      data: { location: { name: 'Shrine (template)', kind: 'building', campaign_id: seeded.world, is_template: true } },
    });
    expect(template.status(), await template.text()).toBe(201);
    const synced = (await (await request.get(`/api/v1/world_entity?campaign_id=${seeded.world}`)).json()) as { world_entities: { name: string }[] };
    expect(synced.world_entities.map((entity) => entity.name)).not.toContain('Shrine (template)');
    // S4c: aliases, lorebook keys and a person's voice reach the sync.
    const mira = (synced.world_entities as { name: string; aliases?: string[]; keywords?: string[]; voice?: { personality: string } | null }[]).find((entity) => entity.name === 'Mira of the Lantern');
    expect([mira?.aliases, mira?.keywords, mira?.voice?.personality]).toEqual([['The Lantern Keeper'], ['harbour light'], 'Patient, watchful, kind to sailors.']);
    // S4d: a lorebook entry's activation reaches the sync, filled with the contract's defaults.
    const flicker = await request.post('/api/v1/journal', {
      data: { journal: { name: 'The Flicker', kind: 'lore', campaign_id: seeded.world, keywords: ['flicker'], lore: { position: 'at_depth', depth: 2 } } },
    });
    expect(flicker.status(), await flicker.text()).toBe(201);
    const withLore = (await (await request.get(`/api/v1/world_entity?campaign_id=${seeded.world}`)).json()) as { world_entities: { name: string; lore: { position: string; probability: number } | null }[] };
    expect(withLore.world_entities.find((entity) => entity.name === 'The Flicker')?.lore).toMatchObject({ position: 'at_depth', probability: 100 });
    // The sandbox cast read by id (rpg-ai): in the order asked, an unknown id absent.
    const cast = (await (await request.get(`/api/v1/world_entity?ids=${seeded.location},no-such-id,${seeded.person}`)).json()) as { world_entities: { name: string }[]; next: null };
    expect([cast.world_entities.map((entity) => entity.name), cast.next]).toEqual([['Port Gull', 'Mira of the Lantern'], null]);
    // Parity: a record kept to the GM says so, and only it.
    const secrets = (await (await request.get(`/api/v1/world_entity?ids=${seeded.journal},${seeded.person}`)).json()) as { world_entities: { gm_only: boolean }[] };
    expect(secrets.world_entities.map((entity) => entity.gm_only)).toEqual([true, false]);
    // Parity's data bank: each record's full text, journals first, the GM's own marked.
    const bank = (await (await request.get(`/api/v1/campaign_document?campaign_id=${seeded.world}`)).json()) as { campaign_documents: { id: string; kind: string; text: string; gm_only: boolean }[] };
    expect(bank.campaign_documents[0]?.kind).toBe('journal');
    expect(bank.campaign_documents.find((one) => one.id === seeded.journal)).toMatchObject({ text: 'The party was ambushed on the rocks.', gm_only: true });
    // The world tick: the clock starts at day 1, 08:00 and advances; the GM moves Mira, and the move is kept.
    expect(await (await request.get(`/api/v1/campaign/${seeded.world}/clock`)).json()).toEqual({ minutes: 480, day: 1, time: '08:00', reason: null });
    const ticked = await request.post(`/api/v1/campaign/${seeded.world}/clock`, { data: { clock: { minutes: 90, reason: 'Night watch' } } });
    expect(await ticked.json()).toEqual({ minutes: 570, day: 1, time: '09:30', reason: 'Night watch' });
    const coast = ((await (await request.get(`/api/v1/world_entity?ids=${seeded.location}`)).json()) as { world_entities: { parent_id: string }[] }).world_entities[0]!.parent_id;
    const walk = await request.post('/api/v1/person_move', { data: { person_move: { person_id: seeded.person, to_location_id: coast, reason: 'Checks the cliffs' } } });
    expect(walk.status(), await walk.text()).toBe(201);
    expect(((await walk.json()) as { person_move: { from_location_id: string; at_minutes: number } }).person_move).toMatchObject({ from_location_id: seeded.location, at_minutes: 570 });
    // And back, so the pages below show her where the seed put her.
    await request.post('/api/v1/person_move', { data: { person_move: { person_id: seeded.person, to_location_id: seeded.location } } });
    // "A voice per character": the picker sets it on the person's own route; the rows serve it.
    const voiced = await request.get(`/api/v1/person/${seeded.person}`);
    const picked = await request.put(`/api/v1/person/${seeded.person}`, { data: { person: { tts_voice: 'onyx' } }, headers: { 'If-Match': voiced.headers().etag ?? '' } });
    expect(picked.status(), await picked.text()).toBe(200);
    const heard = (await (await request.get(`/api/v1/world_entity?ids=${seeded.person}`)).json()) as { world_entities: { tts_voice: string | null }[] };
    expect(heard.world_entities[0]!.tts_voice).toBe('onyx');
    // Parity's party fix: tag names, and a person's ties to other people.
    const party = (await (await request.get(`/api/v1/world_entity?ids=${seeded.person}`)).json()) as { world_entities: { tags: string[]; relationships: { kind: string }[] }[] };
    expect(party.world_entities[0]).toMatchObject({ tags: ['Elf', 'Lamplighters'], relationships: [{ kind: 'rival' }] });
    // Parity: where a person is and a place's parent, so a scene knows who's present.
    const placed = (await (await request.get(`/api/v1/world_entity?ids=${seeded.person},${seeded.location}`)).json()) as { world_entities: { location_id: string | null; parent_id: string | null }[] };
    expect(placed.world_entities.map((entity) => [entity.location_id, entity.parent_id !== null])).toEqual([[seeded.location, false], [null, true]]);
    // Copy on start: a playthrough of the scenario, every record its own copy, references turned to the copies.
    // It answers 202 with a start; GET /v1/campaign_start/{id} has the playthrough (lite's is done at once).
    const started = await request.post(`/api/v1/campaign/${seeded.world}/instantiate`, { data: { instantiate: { name: 'The Salt Coast, run 1' } } });
    expect(started.status(), await started.text()).toBe(202);
    const { start } = (await started.json()) as { start: { id: string; state: string } };
    const report = (await (await request.get(`/api/v1/campaign_start/${start.id}`)).json()) as { campaign_start: { state: string; campaign_id: string; id_map: string } };
    expect(report.campaign_start.state).toBe('done');
    const campaign = ((await (await request.get(`/api/v1/campaign/${report.campaign_start.campaign_id}`)).json()) as { campaign: { id: string; scenario_id: string; is_scenario: boolean } }).campaign;
    const run = { campaign, id_map: JSON.parse(report.campaign_start.id_map) as Record<string, string> };
    expect([run.campaign.scenario_id, run.campaign.is_scenario, run.id_map[seeded.world]]).toEqual([seeded.world, false, run.campaign.id]);
    const copiedMira = (await (await request.get(`/api/v1/person/${run.id_map[seeded.person]}`)).json()) as { person: { name: string; campaign_id: string; location_id: string } };
    expect(copiedMira.person).toMatchObject({ name: 'Mira of the Lantern', campaign_id: run.campaign.id, location_id: run.id_map[seeded.location] });
    // A narrator's unnamed NPC who speaks joins the cast: made once (GM only), then found by name.
    const barkeep = (await (await request.post(`/api/v1/campaign/${seeded.world}/person`, { data: { person: { name: 'The Barkeep', summary: 'Pours, listens.' } } })).json()) as { person: { id: string; created: boolean } };
    expect(barkeep.person.created).toBe(true);
    const again = (await (await request.post(`/api/v1/campaign/${seeded.world}/person`, { data: { person: { name: 'the barkeep' } } })).json()) as { person: { id: string; created: boolean } };
    expect(again.person).toEqual({ id: barkeep.person.id, name: 'The Barkeep', created: false });
    const hidden = (await (await request.get(`/api/v1/record_metadata/of?target_entity_type=person&target_entity_id=${barkeep.person.id}`)).json()) as { metadata: { key: string; value: string }[] };
    expect(hidden.metadata.map((row) => [row.key, row.value]).sort()).toEqual([['GM only', 'true'], ['Made in play', 'By the narrator']]);
    // The narrator's relevance read: only what the text names.
    const named = (await (await request.post(`/api/v1/campaign/${seeded.world}/matching`, { data: { matching: { text: 'Mira of the Lantern lights the lamps.' } } })).json()) as { world_entities: { id: string }[]; matched: Record<string, string[]> };
    expect(named.world_entities.map((entity) => entity.id)).toContain(seeded.person);
    expect(named.matched[seeded.person]).toContain('mira of the lantern');
    // The hybrid lore search (better-sqlite3 + sqlite-vec): her passage first, named; FTS5 ran.
    const lore = await request.post(`/api/v1/campaign/${seeded.world}/lore_search`, { data: { lore_search: { text: 'Mira of the Lantern lights the lamps.' } } });
    expect(lore.status(), await lore.text()).toBe(200);
    const searched = (await lore.json()) as { passages: { record_id: string; ranks: Record<string, number> }[]; methods: Record<string, string> };
    expect(searched.passages[0]).toMatchObject({ record_id: seeded.person, ranks: { exact: 1 } });
    expect(searched.methods.text).toBe('used (FTS5)');
    // The narrator's frame, read from the campaign itself (Parity's campaign_framing).
    const framed = (await (await request.get(`/api/v1/campaign/${seeded.world}/framing`)).json()) as { campaign_framing: { campaign_id: string; play_styles: string[]; from_scenario: boolean; setting: { id: string } | null } };
    expect(framed.campaign_framing).toMatchObject({ campaign_id: seeded.world, from_scenario: false, setting: { id: seeded.setting } });
    expect(framed.campaign_framing.play_styles).toContain('mystery');
    // The setting's pregens: listed for a party picker, and a picked one copied in on a start.
    const made = async (resource: string, body: Record<string, unknown>): Promise<string> =>
      ((await (await request.post(`/api/v1/${resource}`, { data: { [resource]: body } })).json()) as Record<string, { id: string }>)[resource]!.id;
    const akra = await made('person', { name: 'Akra (Dragonborn Cleric, 2014)', kind: 'pc', setting_id: seeded.setting });
    for (const name of ['Pregen', 'Cleric']) {
      const taxon = await made('taxon', { name, kind: 'category', setting_id: seeded.setting });
      await made('entity_taxon', { taxon_id: taxon, target_entity_type: 'person', target_entity_id: akra });
    }
    const pregenList = (await (await request.get(`/api/v1/setting/${seeded.setting}/pregen`)).json()) as { pregens: { id: string; tags: string[] }[] };
    expect(pregenList.pregens).toEqual([expect.objectContaining({ id: akra, tags: ['Pregen', 'Cleric'] })]);
    const withParty = (await (await request.post(`/api/v1/campaign/${seeded.world}/instantiate`, { data: { instantiate: { name: 'With Akra', pregens: [akra] } } })).json()) as { start: { id_map: string; campaign_id: string } };
    const partyMap = JSON.parse(withParty.start.id_map) as Record<string, string>;
    const copiedAkra = (await (await request.get(`/api/v1/person/${partyMap[akra]}`)).json()) as { person: { campaign_id: string } };
    expect(copiedAkra.person.campaign_id).toBe(withParty.start.campaign_id);
    // An NPC authored in the playthrough: filled in by an agent, then elevated to the scenario.
    const npc = ((await (await request.post(`/api/v1/campaign/${run.campaign.id}/person`, { data: { person: { name: 'Old Tam' } } })).json()) as { person: { id: string } }).person;
    const filled = await request.post(`/api/v1/campaign/${run.campaign.id}/fill_person`, { data: { person: { person_id: npc.id, summary: 'Keeps the inn.', personality: 'Gruff', motive: 'Pay the Guild' } } });
    expect(filled.status(), await filled.text()).toBe(200);
    const lifted = (await (await request.post(`/api/v1/campaign/${run.campaign.id}/elevate`, { data: { elevate: { person_id: npc.id } } })).json()) as { elevated: { scenario_person_id: string; scenario_id: string; created: boolean } };
    expect([lifted.elevated.scenario_id, lifted.elevated.created]).toEqual([seeded.world, true]);
    const twin = (await (await request.get(`/api/v1/person/${lifted.elevated.scenario_person_id}`)).json()) as { person: { name: string; campaign_id: string } };
    expect(twin.person).toMatchObject({ name: 'Old Tam', campaign_id: seeded.world });
    const liftedAgain = (await (await request.post(`/api/v1/campaign/${run.campaign.id}/elevate`, { data: { elevate: { person_id: npc.id } } })).json()) as { elevated: { scenario_person_id: string; created: boolean } };
    expect(liftedAgain.elevated).toMatchObject({ scenario_person_id: lifted.elevated.scenario_person_id, created: false });
    const original = (await (await request.get(`/api/v1/person/${seeded.person}`)).json()) as { person: { campaign_id: string } };
    expect(original.person.campaign_id).toBe(seeded.world);
    const pages = worldPages(seeded);
    const page = await browser.newPage({ baseURL: String(testInfo.project.use.baseURL) });
    await expectSeedShows(page, seeded);
    await page.close();
    test.setTimeout(pages.length * 6 * PER_SHOT_MS + 30_000);
    await audit(browser, testInfo, 'world', pages);
    await voiceEditor(browser, testInfo, `/w/${seeded.world}/person/${seeded.person}`);
  });
});

/** The voice editor open (Parity's prompt parts included), at each size, light: it must fit. */
async function voiceEditor(browser: Browser, testInfo: TestInfo, target: string): Promise<void> {
  for (const [size, device] of Object.entries(VIEWPORTS)) {
    const context = await browser.newContext({ ...device, baseURL: String(testInfo.project.use.baseURL) });
    const page = await context.newPage();
    try {
      await page.goto(target);
      await page.getByRole('button', { name: 'Edit voice' }).click();
      await expect(page.getByLabel('Talkativeness')).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${target} voice editor (${size}): sideways overflow`).toBeLessThanOrEqual(0);
      if (AUDIT_DIR !== '') await page.screenshot({ path: path.join(AUDIT_DIR, `${testInfo.project.name}-voice-editor-${size}.png`), fullPage: true });
    } finally {
      await context.close();
    }
  }
}
