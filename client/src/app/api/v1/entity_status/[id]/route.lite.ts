// SPDX-License-Identifier: AGPL-3.0-or-later
import { localOwner, recordRoutes } from '@zephyrex/lite';
import { entityStatuses } from '~/lib/worldRecords';

// GET, PUT (If-Match) and DELETE (If-Match) /v1/entity_status/{id}.
export const { GET, PUT, DELETE } = recordRoutes(entityStatuses, localOwner);
