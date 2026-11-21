// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { entityStatuses } from '~/lib/worldRecords';

// GET /v1/entity_status (list) and POST /v1/entity_status (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(entityStatuses, localOwner);
