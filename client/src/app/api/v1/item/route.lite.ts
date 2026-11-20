// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { items } from '~/lib/worldRecords';

// GET /v1/item (list) and POST /v1/item (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(items, localOwner);
