// SPDX-License-Identifier: AGPL-3.0-or-later
import { localOwner, recordRoutes } from '@zephyrex/lite';
import { personHooks } from '~/lib/worldRecords';

// GET, PUT (If-Match) and DELETE (If-Match) /v1/person_hook/{id}.
export const { GET, PUT, DELETE } = recordRoutes(personHooks, localOwner);
