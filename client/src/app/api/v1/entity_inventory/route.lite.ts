// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { entityInventories } from '~/lib/worldRecords';

// GET /v1/entity_inventory (list) and POST /v1/entity_inventory (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(entityInventories, localOwner);
