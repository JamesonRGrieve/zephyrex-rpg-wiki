// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { journals } from '~/lib/worldRecords';

// GET /v1/journal (list) and POST /v1/journal (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(journals, localOwner);
