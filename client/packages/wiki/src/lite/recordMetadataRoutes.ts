// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * /v1/record_metadata, as the framework's metadata extension answers it (S4b): POST adds a
 * key/value to a record, PATCH /{id} changes one, DELETE /{id} removes one, and GET /of lists a
 * record's in order. Only the record's owner reads or writes them.
 */
import { apiErrorResponse, localOwner, parseBody, readJsonObject, STATUS, validationError } from '@zephyrex/lite';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { addRow, changeRow, metadataChange, metadataOf, metadataWrite, removeRow, rowsOn } from './recordMetadata';

type Context = { params: Promise<Record<string, string>> };

export async function metadataPost(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const input = parseBody(metadataWrite, await readJsonObject(request), 'record_metadata');
    return NextResponse.json({ record_metadata: metadataOf(await addRow(owner.id, input)) }, { status: STATUS.CREATED });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

export async function metadataPatch(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const id = (await context.params).id ?? '';
    const input = parseBody(metadataChange, await readJsonObject(request), 'record_metadata');
    return NextResponse.json({ record_metadata: metadataOf(await changeRow(id, owner.id, input)) });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

export async function metadataDelete(request: NextRequest, context: Context): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    await removeRow((await context.params).id ?? '', owner.id);
    return new NextResponse(null, { status: STATUS.NO_CONTENT });
  } catch (error) {
    return apiErrorResponse(error);
  }
}

export async function metadataOfGet(request: NextRequest): Promise<NextResponse> {
  try {
    const owner = await localOwner(request);
    const query = request.nextUrl.searchParams;
    const type = query.get('target_entity_type') ?? '';
    const id = query.get('target_entity_id') ?? '';
    if (type === '' || id === '') throw validationError('Name the record: target_entity_type and target_entity_id', 'target_entity_id');
    return NextResponse.json({ metadata: (await rowsOn(type, id, owner.id)).map(metadataOf) });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
