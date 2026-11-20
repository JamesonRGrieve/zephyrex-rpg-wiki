// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { factions } from '~/lib/worldRecords';

// GET /v1/faction (list) and POST /v1/faction (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(factions, localOwner);
