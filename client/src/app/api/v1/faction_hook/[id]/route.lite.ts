// SPDX-License-Identifier: AGPL-3.0-or-later
import { localOwner, recordRoutes } from '@zephyrex/lite';
import { factionHooks } from '~/lib/worldRecords';

// GET, PUT (If-Match) and DELETE (If-Match) /v1/faction_hook/{id}.
export const { GET, PUT, DELETE } = recordRoutes(factionHooks, localOwner);
