// SPDX-License-Identifier: AGPL-3.0-or-later
import { localOwner, recordRoutes } from '@zephyrex/lite';
import { items } from '~/lib/worldRecords';

// GET, PUT (If-Match) and DELETE (If-Match) /v1/item/{id}.
export const { GET, PUT, DELETE } = recordRoutes(items, localOwner);
