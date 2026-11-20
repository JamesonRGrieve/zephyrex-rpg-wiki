// SPDX-License-Identifier: AGPL-3.0-or-later
import { localOwner, recordRoutes } from '@zephyrex/lite';
import { locations } from '~/lib/worldRecords';

// GET, PUT (If-Match) and DELETE (If-Match) /v1/location/{id}.
export const { GET, PUT, DELETE } = recordRoutes(locations, localOwner);
