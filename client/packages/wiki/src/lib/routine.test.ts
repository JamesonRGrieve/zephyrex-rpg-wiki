// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from 'vitest';
import cases from '../../../../../contract/routine-cases.json';
import { clock, invariants, motivations, routine } from './routine';

describe('routine, motivations and clock (contract/routine-cases.json)', () => {
  it.each(cases.routines)('reads the routine: $name', ({ value, checked }) => {
    expect(routine(value)).toEqual(checked);
  });
  it.each(cases.invalid_routines)('refuses the routine: $name', ({ value, message }) => {
    expect(() => routine(value)).toThrow(message);
  });
  it.each(cases.motivations)('reads motivations: $name', ({ value, checked }) => {
    expect(motivations(value)).toEqual(checked);
  });
  it.each(cases.invalid_motivations)('refuses motivations: $name', ({ value, message }) => {
    expect(() => motivations(value)).toThrow(message);
  });
  it.each(cases.invariants)('reads invariants: $name', ({ value, checked }) => {
    expect(invariants(value)).toEqual(checked);
  });
  it.each(cases.invalid_invariants)('refuses invariants: $name', ({ value, message }) => {
    expect(() => invariants(value)).toThrow(message);
  });
  it.each(cases.clocks)('reads the clock: $name', ({ minutes, clock: expected }) => {
    expect(clock(minutes)).toEqual(expected);
  });
});
