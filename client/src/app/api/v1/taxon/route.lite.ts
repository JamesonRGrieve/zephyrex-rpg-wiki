// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { taxa } from '~/lib/worldRecords';

// GET /v1/taxon (list) and POST /v1/taxon (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(taxa, localOwner);
