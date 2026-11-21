// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { propertyKits } from '~/lib/worldRecords';

// GET /v1/property_kit (list) and POST /v1/property_kit (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(propertyKits, localOwner);
