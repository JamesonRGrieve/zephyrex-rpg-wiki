// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { entityPosts } from '~/lib/worldRecords';

// GET /v1/entity_post (list) and POST /v1/entity_post (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(entityPosts, localOwner);
