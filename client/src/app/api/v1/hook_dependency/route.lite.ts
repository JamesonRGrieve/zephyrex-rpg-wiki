// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { hookDependencies } from '~/lib/worldRecords';

// GET /v1/hook_dependency (list) and POST /v1/hook_dependency (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(hookDependencies, localOwner);
