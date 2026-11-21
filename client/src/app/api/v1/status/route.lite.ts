// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { statuses } from '~/lib/worldRecords';

// GET /v1/status (list) and POST /v1/status (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(statuses, localOwner);
