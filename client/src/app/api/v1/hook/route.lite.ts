// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { hooks } from '~/lib/worldRecords';

// GET /v1/hook (list) and POST /v1/hook (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(hooks, localOwner);
