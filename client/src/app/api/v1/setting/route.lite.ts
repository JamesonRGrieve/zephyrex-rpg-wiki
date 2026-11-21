// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { settings } from '~/lib/worldRecords';

// GET /v1/setting (list) and POST /v1/setting (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(settings, localOwner);
