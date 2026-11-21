// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { relationships } from '~/lib/worldRecords';

// GET /v1/relationship (list) and POST /v1/relationship (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(relationships, localOwner);
