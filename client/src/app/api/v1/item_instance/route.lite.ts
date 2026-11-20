// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { itemInstances } from '~/lib/worldRecords';

// GET /v1/item_instance (list) and POST /v1/item_instance (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(itemInstances, localOwner);
