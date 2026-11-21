// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { factionHooks } from '~/lib/worldRecords';

// GET /v1/faction_hook (list) and POST /v1/faction_hook (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(factionHooks, localOwner);
