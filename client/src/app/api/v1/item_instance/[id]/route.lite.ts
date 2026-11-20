// SPDX-License-Identifier: AGPL-3.0-or-later
import { localOwner, recordRoutes } from '@zephyrex/lite';
import { itemInstances } from '~/lib/worldRecords';

// GET, PUT (If-Match) and DELETE (If-Match) /v1/item_instance/{id}.
export const { GET, PUT, DELETE } = recordRoutes(itemInstances, localOwner);
