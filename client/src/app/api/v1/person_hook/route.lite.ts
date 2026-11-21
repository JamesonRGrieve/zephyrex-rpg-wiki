// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { personHooks } from '~/lib/worldRecords';

// GET /v1/person_hook (list) and POST /v1/person_hook (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(personHooks, localOwner);
