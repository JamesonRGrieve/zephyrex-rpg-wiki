// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A person's routine, motivations and invariants, and a campaign's clock (contract/routine-cases.json), as the
 * server's wiki_shared/Routine.py reads them: the GM side's world tick pilots people by them.
 */
import { CLOCK_START_MINUTES, LIMITS } from '../contract';

export type Slot = {
  from: string;
  to: string;
  /** 0 (Monday) to 6, or every day (null). */
  days: number[] | null;
  location_id: string | null;
  activity: string;
};
export type Clock = { minutes: number; day: number; time: string };

const PARTS = ['from', 'to', 'days', 'location_id', 'activity'];
const TIME = /^([01]\d|2[0-3]):[0-5]\d$/;
const MINUTES_A_DAY = 24 * 60;
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);
const loaded = (value: unknown): unknown => (typeof value === 'string' ? JSON.parse(value) : value);

function slot(value: unknown): Slot {
  if (!isRecord(value) || Object.keys(value).some((key) => !PARTS.includes(key))) throw new Error('A slot is from, to, days, location_id and activity');
  const { from, to } = value;
  if (typeof from !== 'string' || typeof to !== 'string' || !TIME.test(from) || !TIME.test(to)) throw new Error('A slot runs from HH:MM to HH:MM');
  let days: number[] | null = null;
  if (value.days !== undefined && value.days !== null) {
    if (!Array.isArray(value.days) || value.days.some((day) => typeof day !== 'number' || !Number.isInteger(day) || day < 0 || day > 6))
      throw new Error("A slot's days are 0 (Monday) to 6");
    days = [...new Set(value.days as number[])].sort((one, two) => one - two);
  }
  const location = value.location_id ?? null;
  if (location !== null && typeof location !== 'string') throw new Error("A slot's location_id is a record's id");
  const activity = value.activity ?? '';
  if (typeof activity !== 'string' || activity.length > LIMITS.activity_characters)
    throw new Error(`A slot's activity is text of at most ${LIMITS.activity_characters} characters`);
  return { from, to, days, location_id: location === '' ? null : location, activity: activity.trim() };
}

export function routine(value: unknown): Slot[] {
  const given = loaded(value);
  if (!Array.isArray(given)) throw new Error('A routine is a list of slots');
  if (given.length > LIMITS.routine_slots) throw new Error(`A routine has at most ${LIMITS.routine_slots} slots`);
  return given.map(slot).sort((one, two) => one.from.localeCompare(two.from) || one.to.localeCompare(two.to));
}

/** A list of text trimmed, each once, blanks dropped: at most ``most`` of ``characters`` each. */
function texts(value: unknown, what: string, most: number, characters: number): string[] {
  const given = loaded(value);
  if (!Array.isArray(given) || given.some((one) => typeof one !== 'string')) throw new Error(`${what[0]!.toUpperCase()}${what.slice(1)} are a list of text`);
  const kept = [...new Set((given as string[]).map((one) => one.trim()).filter((one) => one !== ''))];
  if (kept.length > most || kept.some((one) => one.length > characters)) throw new Error(`At most ${most} ${what} of at most ${characters} characters`);
  return kept;
}

export function motivations(value: unknown): string[] {
  return texts(value, 'motivations', LIMITS.motivations, LIMITS.motivation_characters);
}

/** The lines a person never crosses ("never harms a child"; operator, 2026-11-28). */
export function invariants(value: unknown): string[] {
  return texts(value, 'invariants', LIMITS.invariants, LIMITS.invariant_characters);
}

export function storedRoutine(text: string | null | undefined): Slot[] {
  try {
    return text ? routine(text) : [];
  } catch {
    return [];
  }
}

export function storedMotivations(text: string | null | undefined): string[] {
  try {
    return text ? motivations(text) : [];
  } catch {
    return [];
  }
}

export function storedInvariants(text: string | null | undefined): string[] {
  try {
    return text ? invariants(text) : [];
  } catch {
    return [];
  }
}

/** A campaign's clock: its minutes (a new one at clock_start_minutes), its day and its time. */
export function clock(minutes: number | null | undefined): Clock {
  const held = minutes ?? CLOCK_START_MINUTES;
  const pad = (value: number): string => String(value).padStart(2, '0');
  return { minutes: held, day: Math.floor(held / MINUTES_A_DAY) + 1, time: `${pad(Math.floor((held % MINUTES_A_DAY) / 60))}:${pad(held % 60)}` };
}
