// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { entityTaxa } from '~/lib/worldRecords';

// GET /v1/entity_taxon (list) and POST /v1/entity_taxon (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(entityTaxa, localOwner);
