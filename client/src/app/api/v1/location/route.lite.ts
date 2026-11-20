// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { locations } from '~/lib/worldRecords';

// GET /v1/location (list) and POST /v1/location (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(locations, localOwner);
