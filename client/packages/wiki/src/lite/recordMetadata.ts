// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * A record's own key/values (S4b), as the framework's /v1/record_metadata answers them: rows on a
 * record by type and id, one per key, in order (ordinal, then key). Lite has one person, who sees
 * and edits all their records, so a private row only matters to the server's other users.
 */
import type { Prisma } from '@prisma/client';
import { ApiError, recordError, STATUS, validationError } from '@zephyrex/lite';
import { z } from 'zod';
import { LIMITS, PROPERTY_VALUE_TYPES } from '../contract';
import { prisma } from './db';

type MetadataRow = Prisma.RecordMetadataGetPayload<object>;

/** The record types a property may sit on, and whether one of the owner's records has that id. */
const RECORDS: Record<string, (id: string, ownerId: string) => Promise<number>> = {
  person: (id, ownerId) => prisma.person.count({ where: { id, createdById: ownerId, deletedAt: null } }),
  location: (id, ownerId) => prisma.location.count({ where: { id, createdById: ownerId, deletedAt: null } }),
  faction: (id, ownerId) => prisma.faction.count({ where: { id, createdById: ownerId, deletedAt: null } }),
  item: (id, ownerId) => prisma.item.count({ where: { id, createdById: ownerId, deletedAt: null } }),
  journal: (id, ownerId) => prisma.journal.count({ where: { id, createdById: ownerId, deletedAt: null } }),
  hook: (id, ownerId) => prisma.hook.count({ where: { id, createdById: ownerId, deletedAt: null } }),
};

/** The same 404 whether the record is missing or merely not the owner's, as the server; an unknown type is a 422. */
export async function requireRecord(type: string, id: string, ownerId: string): Promise<void> {
  const counts = RECORDS[type];
  if (counts === undefined) throw validationError(`Unknown record type: ${type}`, 'target_entity_type');
  if ((await counts(id, ownerId)) === 0) throw recordError(STATUS.NOT_FOUND, 'Record not found');
}

/** A row as the server's MetadataModel. */
export function metadataOf(row: MetadataRow): Record<string, unknown> {
  return {
    id: row.id,
    key: row.key,
    value: row.value,
    value_type: row.valueType,
    ordinal: row.ordinal,
    is_private: row.isPrivate,
    target_entity_type: row.targetEntityType,
    target_entity_id: row.targetEntityId,
    user_id: null,
    team_id: null,
    created_at: row.createdAt.toISOString(),
    updated_at: row.updatedAt.toISOString(),
  };
}

const valueType = z.enum(PROPERTY_VALUE_TYPES as [string, ...string[]], {
  message: `value_type is one of ${PROPERTY_VALUE_TYPES.join(', ')}`,
});
const key = z.string().min(1).max(LIMITS.property_key_characters);
const value = z.string().max(LIMITS.property_value_characters).nullable();

export const metadataWrite = z.object({
  target_entity_type: z.string().min(1),
  target_entity_id: z.string().min(1),
  key,
  value: value.default(null),
  value_type: valueType.nullable().default(null),
  ordinal: z.number().int().default(0),
  is_private: z.boolean().default(false),
});
export const metadataChange = z.object({ key, value, value_type: valueType.nullable(), ordinal: z.number().int(), is_private: z.boolean() }).partial();

/** A record's rows, in order. */
export async function rowsOn(type: string, id: string, ownerId: string): Promise<MetadataRow[]> {
  await requireRecord(type, id, ownerId);
  const rows = await prisma.recordMetadata.findMany({ where: { targetEntityType: type, targetEntityId: id } });
  return rows.sort((a, b) => a.ordinal - b.ordinal || a.key.localeCompare(b.key));
}

/** Adds a key to a record: 409 when it has the key, 422 past the record's keys, as the server. */
export async function addRow(ownerId: string, input: z.infer<typeof metadataWrite>): Promise<MetadataRow> {
  const held = await rowsOn(input.target_entity_type, input.target_entity_id, ownerId);
  if (held.some((row) => row.key === input.key)) throw new ApiError(STATUS.CONFLICT, `The record already has '${input.key}'`);
  if (held.length >= LIMITS.properties_per_record) throw validationError(`A record has at most ${LIMITS.properties_per_record} keys`, 'key');
  return prisma.recordMetadata.create({
    data: {
      createdById: ownerId,
      targetEntityType: input.target_entity_type,
      targetEntityId: input.target_entity_id,
      key: input.key,
      value: input.value,
      valueType: input.value_type,
      ordinal: input.ordinal,
      isPrivate: input.is_private,
      updatedAt: new Date(),
    },
  });
}

async function ownRow(id: string, ownerId: string): Promise<MetadataRow> {
  const row = await prisma.recordMetadata.findUnique({ where: { id } });
  if (row === null) throw recordError(STATUS.NOT_FOUND, 'Not found');
  await requireRecord(row.targetEntityType, row.targetEntityId, ownerId);
  return row;
}

/** Changes a row: 409 when renamed to a key the record already has. */
export async function changeRow(id: string, ownerId: string, input: z.infer<typeof metadataChange>): Promise<MetadataRow> {
  const row = await ownRow(id, ownerId);
  if (input.key !== undefined && input.key !== row.key) {
    const clash = await prisma.recordMetadata.count({
      where: { targetEntityType: row.targetEntityType, targetEntityId: row.targetEntityId, key: input.key },
    });
    if (clash > 0) throw new ApiError(STATUS.CONFLICT, `The record already has '${input.key}'`);
  }
  return prisma.recordMetadata.update({
    where: { id },
    data: {
      ...(input.key === undefined ? {} : { key: input.key }),
      ...(input.value === undefined ? {} : { value: input.value }),
      ...(input.value_type === undefined ? {} : { valueType: input.value_type }),
      ...(input.ordinal === undefined ? {} : { ordinal: input.ordinal }),
      ...(input.is_private === undefined ? {} : { isPrivate: input.is_private }),
      updatedAt: new Date(),
      updatedById: ownerId,
    },
  });
}

export async function removeRow(id: string, ownerId: string): Promise<void> {
  await ownRow(id, ownerId);
  await prisma.recordMetadata.delete({ where: { id } });
}
