// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { people } from '~/lib/worldRecords';

// GET /v1/person (list) and POST /v1/person (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(people, localOwner);
