// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { relationInfluences } from '~/lib/worldRecords';

// GET /v1/relation_influence (list) and POST /v1/relation_influence (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(relationInfluences, localOwner);
