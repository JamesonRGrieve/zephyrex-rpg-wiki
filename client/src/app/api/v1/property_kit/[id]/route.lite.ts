// SPDX-License-Identifier: AGPL-3.0-or-later
import { localOwner, recordRoutes } from '@zephyrex/lite';
import { propertyKits } from '~/lib/worldRecords';

// GET, PUT (If-Match) and DELETE (If-Match) /v1/property_kit/{id}.
export const { GET, PUT, DELETE } = recordRoutes(propertyKits, localOwner);
