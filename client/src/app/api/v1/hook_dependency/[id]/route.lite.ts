// SPDX-License-Identifier: AGPL-3.0-or-later
import { localOwner, recordRoutes } from '@zephyrex/lite';
import { hookDependencies } from '~/lib/worldRecords';

// GET, PUT (If-Match) and DELETE (If-Match) /v1/hook_dependency/{id}.
export const { GET, PUT, DELETE } = recordRoutes(hookDependencies, localOwner);
