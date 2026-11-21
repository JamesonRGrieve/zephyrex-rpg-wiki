// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A small world, made through the API as a person would through the app: places, people,
 * organisations, items, journals, hooks, tags, a status and relations, so every page has
 * something in it. Returns the ids the audit visits.
 */
import { expect, type APIRequestContext } from '@playwright/test';

export interface Seeded {
  setting: string;
  world: string;
  location: string;
  person: string;
  faction: string;
  item: string;
  journal: string;
  hook: string;
  taxon: string;
}

async function create(request: APIRequestContext, resource: string, fields: Record<string, unknown>): Promise<string> {
  const response = await request.post(`/api/v1/${resource}`, { data: { [resource]: fields } });
  expect(response.status(), `${resource}: ${await response.text()}`).toBe(201);
  const body = (await response.json()) as Record<string, { id: string }>;
  return body[resource]!.id;
}

const entry = (text: string) => [{ type: 'p', children: [{ text }] }];

export async function seedWorld(request: APIRequestContext): Promise<Seeded> {
  // A setting (S6) encloses the world; its campaign-less records are its canon.
  const setting = await create(request, 'setting', { name: 'The Grim Future', entry: entry('Ten thousand years of war.') });
  const world = await create(request, 'campaign', { name: 'The Salt Coast', setting_id: setting, provenance: 'adapted', source: 'Salt and Storm, Harbour Press, ch. 2' });
  await create(request, 'faction', { name: 'Adeptus Mechanicus', kind: 'religious', setting_id: setting, canon_level: 'common' });
  const coast = await create(request, 'location', { name: 'Salt Coast', kind: 'region', campaign_id: world, entry: entry('Cliffs, coves and smugglers.') });
  const location = await create(request, 'location', {
    name: 'Port Gull',
    kind: 'city',
    parent_id: coast,
    campaign_id: world,
    entry: entry('A port city of narrow stairs and salt-stained walls.'),
  });
  const person = await create(request, 'person', {
    name: 'Mira of the Lantern',
    kind: 'npc',
    campaign_id: world,
    location_id: location,
    entry: entry('Keeper of the harbour light.'),
    // S4c: other names, lorebook keys and how the AI plays her.
    aliases: ['The Lantern Keeper'],
    keywords: ['harbour light'],
    voice: {
      personality: 'Patient, watchful, kind to sailors.',
      speech: 'Speaks softly, in tides and weather.',
      first_message: 'The light holds. What brings you up the stair?',
      examples: ['Mira: Mind the seventh step.'],
      // Parity: a SillyTavern card's own prompt parts.
      system_prompt: 'You are Mira, keeper of the harbour light at Port Gull.',
      depth_prompt: { prompt: 'Mira never leaves the lantern unattended after dusk.', depth: 2, role: 'system' },
      talkativeness: 0.4,
    },
  });
  const rival = await create(request, 'person', { name: 'Captain Ross', kind: 'npc', campaign_id: world });
  const faction = await create(request, 'faction', { name: 'Lantern Guild', kind: 'guild', campaign_id: world, entry: entry('Lamplighters and keepers.') });
  await create(request, 'faction', { name: 'Night Watch', kind: 'military', campaign_id: world });
  const item = await create(request, 'item', {
    name: 'Brass lantern',
    kind: 'misc',
    campaign_id: world,
    entry: entry('Never goes out.'),
    provenance: 'official',
    source: 'Salt and Storm, Harbour Press, p. 41',
  });
  const journal = await create(request, 'journal', {
    name: 'Session 4: the Gull Rock ambush',
    kind: 'session_report',
    session_number: 4,
    campaign_id: world,
    location_id: location,
    entry: entry('The party was ambushed on the rocks.'),
  });
  const find = await create(request, 'hook', { name: 'Find the lost map', kind: 'objective', campaign_id: world, resolved_at: '2026-11-20T10:00:00Z' });
  const hook = await create(request, 'hook', { name: 'Recover the relic', kind: 'major_quest', campaign_id: world, giver_person_id: person, giver_faction_id: faction });
  await create(request, 'hook_dependency', { parent_hook_id: find, child_hook_id: hook });
  await create(request, 'person_hook', { person_id: person, hook_id: hook, status: 'active', progress: 2 });
  await create(request, 'hook', {
    name: 'Hear the vox ghost',
    kind: 'mystery',
    campaign_id: world,
    requires: { all: [find, { char: { skill: ['psyniscience', 'forbidden-lore'] } }] },
  });
  await create(request, 'hook', { name: 'Repair the Geller field', kind: 'objective', campaign_id: world, requires: hook, excuse: 'Rech needs the relic before he can start.' });
  await create(request, 'disposition', { person_id: person, target_kind: 'party', attitude: 'cautious-neutral', is_default: true, note: 'Helpful, volunteers nothing.' });
  await create(request, 'disposition', { person_id: person, target_kind: 'party', attitude: 'guarded', trigger_hook_id: find, note: 'She knows what the map leads to.' });
  const nobility = await create(request, 'taxon', { name: 'Nobility', kind: 'tag', colour: '#a83232', campaign_id: world });
  const taxon = await create(request, 'taxon', { name: 'Lamplighters', kind: 'tag', parent_id: nobility, campaign_id: world });
  const elf = await create(request, 'taxon', { name: 'Elf', kind: 'race', campaign_id: world });
  await create(request, 'entity_taxon', { taxon_id: taxon, target_entity_type: 'person', target_entity_id: person });
  await create(request, 'entity_taxon', { taxon_id: elf, target_entity_type: 'person', target_entity_id: person });
  const alive = await create(request, 'status', { name: 'Alive', kind: 'entity_status', colour: '#32a852', campaign_id: world });
  await create(request, 'entity_status', { status_id: alive, target_entity_type: 'person', target_entity_id: person });
  const serves = await create(request, 'relationship', { person_id: person, target_faction_id: faction, kind: 'serves', intensity: 0.6, colour: '#3260a8' });
  await create(request, 'relationship', { faction_id: faction, target_person_id: person, kind: 'serves', intensity: 0.6, colour: '#3260a8', mirror_relationship_id: serves });
  const rivalry = await create(request, 'relationship', { person_id: person, target_person_id: rival, kind: 'rival', intensity: -0.7 });
  await create(request, 'relation_influence', { relationship_id: rivalry, hook_id: find, to_intensity: -0.2, note: 'The map made them allies of need.' });
  // A session report through rpg-ai's route (A24): created, so 201 in both editions, as the server's.
  await create(request, 'session_report', {
    campaign_id: world,
    title: 'Session 5: the lantern goes dark',
    body: 'Mira keeps the light lit.',
    session_number: 5,
    mentions: [{ target_entity_type: 'person', target_entity_id: person }],
  });
  // S4b: a record's own key/values (the metadata extension's routes, served by lite too).
  await create(request, 'record_metadata', { target_entity_type: 'person', target_entity_id: person, key: 'Lantern oil', value: 'Three flasks' });
  await create(request, 'entity_post', { target_entity_type: 'person', target_entity_id: person, name: 'Rumour', position: 'pinned_top', entry: entry('She once sailed with pirates.') });
  return { setting, world, location, person, faction, item, journal, hook, taxon };
}
