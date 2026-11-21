// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { dispositions } from '~/lib/worldRecords';

// GET /v1/disposition (list) and POST /v1/disposition (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(dispositions, localOwner);
